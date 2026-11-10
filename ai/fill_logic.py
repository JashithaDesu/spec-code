"""Closed AI loop: requirements + generated interface + guardrails -> LLM -> gates -> feedback.

1. Builds a prompt from ai/guardrails.md, requirements/requirements.yaml and the generated
   interface src/generated/service_base.py.
2. Asks a local model through Ollama for src/logic/service.py.
3. Runs the guardrail gate and the acceptance tests.
4. If anything fails, sends the failures back to the model and tries again (up to --attempts).
Every attempt is logged to experiment/ai_attempts.csv for the evaluation.

Usage:
    python ai/fill_logic.py                          # qwen2.5-coder:7b, up to 3 attempts
    python ai/fill_logic.py --model llama3.1:8b --attempts 5
    python ai/fill_logic.py --dry-run                # print the first prompt only
    python ai/fill_logic.py --restore                # undo the change if every attempt fails
Needs Ollama running locally (https://ollama.com): `ollama pull qwen2.5-coder:7b`.
"""
import argparse
import csv
import json
import os
import re
import subprocess
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOGIC = ROOT / "src" / "logic" / "service.py"
LOG = ROOT / "experiment" / "ai_attempts.csv"
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434")
LOG_FIELDS = ["run_id", "attempt", "model", "llm_seconds", "guardrail_problems",
              "tests_passed", "tests_failed", "lines_of_code", "result"]


def build_prompt():
    read = lambda rel: (ROOT / rel).read_text(encoding="utf-8")  # noqa: E731
    return (
        "You are implementing the business logic of a small payment API.\n\n"
        "## Rules\n" + read("ai/guardrails.md") + "\n\n"
        "## Requirements\n```yaml\n" + read("requirements/requirements.yaml") + "```\n\n"
        "## Generated interface you must implement (src/generated/service_base.py)\n"
        "```python\n" + read("src/generated/service_base.py") + "```\n\n"
        "Write the complete file src/logic/service.py. It must start with:\n"
        "from src.generated.service_base import VoucherServiceBase\n"
    )


def extract_code(reply):
    """Return the first python code block, or the whole reply if there is no block."""
    match = re.search(r"```(?:python|py)?\s*\n(.*?)```", reply, re.DOTALL)
    return (match.group(1) if match else reply).strip() + "\n"


def ask_model(model, messages, timeout=600):
    payload = json.dumps({"model": model, "messages": messages, "stream": False,
                          "options": {"temperature": 0}}).encode("utf-8")
    request = urllib.request.Request(f"{OLLAMA_URL}/api/chat", data=payload,
                                     headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read())["message"]["content"]


def run(cmd):
    result = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    return result.returncode, (result.stdout + result.stderr).strip()


def run_gates():
    """Returns (guardrail_problems, passed, failed, feedback_text)."""
    code, guard_out = run([sys.executable, "gates/check_guardrails.py"])
    problems = [line for line in guard_out.splitlines() if re.match(r"G\d", line)]
    if code != 0:
        return len(problems), 0, 0, "Guardrail check failed:\n" + guard_out

    _, test_out = run([sys.executable, "-m", "pytest", "tests", "-q", "-p", "no:cacheprovider",
                       "--tb=line", "-rf"])
    passed = int(m.group(1)) if (m := re.search(r"(\d+) passed", test_out)) else 0
    failed = int(m.group(1)) if (m := re.search(r"(\d+) failed", test_out)) else 0
    errors = int(m.group(1)) if (m := re.search(r"(\d+) error", test_out)) else 0
    failed += errors
    failures = [line for line in test_out.splitlines() if line.startswith(("FAILED", "ERROR", "E "))]
    feedback = "" if failed == 0 else "Acceptance tests failed:\n" + "\n".join(failures[:40])
    return 0, passed, failed, feedback


def log_attempt(row):
    LOG.parent.mkdir(exist_ok=True)
    new_file = not LOG.exists()
    with LOG.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=LOG_FIELDS)
        if new_file:
            writer.writeheader()
        writer.writerow(row)


def main():
    parser = argparse.ArgumentParser(description="Generate src/logic/service.py with a local LLM.")
    parser.add_argument("--model", default="qwen2.5-coder:7b")
    parser.add_argument("--attempts", type=int, default=3)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--restore", action="store_true",
                        help="put the original service.py back if every attempt fails")
    args = parser.parse_args()

    prompt = build_prompt()
    if args.dry_run:
        print(prompt)
        return 0

    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    messages = [{"role": "user", "content": prompt}]
    original = LOGIC.read_text(encoding="utf-8")
    for attempt in range(1, args.attempts + 1):
        start = time.monotonic()
        reply = ask_model(args.model, messages)
        seconds = round(time.monotonic() - start, 1)
        code = extract_code(reply)
        LOGIC.write_text(code, encoding="utf-8")

        guard_problems, passed, failed, feedback = run_gates()
        ok = guard_problems == 0 and failed == 0 and passed > 0
        log_attempt({"run_id": run_id, "attempt": attempt, "model": args.model,
                     "llm_seconds": seconds, "guardrail_problems": guard_problems,
                     "tests_passed": passed, "tests_failed": failed,
                     "lines_of_code": len(code.splitlines()), "result": "pass" if ok else "fail"})
        print(f"Attempt {attempt}: {seconds}s, guardrail problems {guard_problems}, "
              f"tests passed {passed}, failed {failed}")
        if ok:
            print(f"All gates passed. Logged to {LOG.relative_to(ROOT)}.")
            return 0
        messages += [{"role": "assistant", "content": reply},
                     {"role": "user", "content": feedback + "\n\nFix the problems and answer with "
                                                 "the complete corrected file in one code block."}]

    if args.restore:
        LOGIC.write_text(original, encoding="utf-8")
        print(f"Still failing after {args.attempts} attempts; restored the original service.py.")
    else:
        print(f"Still failing after {args.attempts} attempts; the last version is in "
              f"{LOGIC.relative_to(ROOT)} so you can inspect or fix it by hand.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
