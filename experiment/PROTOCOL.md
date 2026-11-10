# Experiment protocol: spec-driven vs code-first

## Question

For the same development tasks, does a specification-driven, AI-assisted workflow
(spec → deterministic generation → AI-written logic → automated gates) differ from a
code-first workflow in lead time, rework, defects and consistency?

## Conditions

| | A. Spec-driven | B. Code-first |
|---|---|---|
| Input | `spec/openapi.yaml` + `requirements/requirements.yaml` | `requirements/requirements.yaml` only (including its prose `interface` section) |
| Generated code | `src/generated/` from `python generator/generate.py` | none |
| Code you write | `src/logic/service.py` | `code_first/app.py` (and any new files under `code_first/`) |
| AI use | `python ai/fill_logic.py` (closed loop with guardrails); manual fixes allowed afterwards | the same model in chat or as a coding assistant, no guardrails or loop |
| Done when | all gates and all acceptance tests pass | all acceptance tests pass with `TARGET=codefirst` |

Use **the same model** in both conditions (default `qwen2.5-coder:7b`), so the difference
comes from the workflow, not from the model.

## Tasks

**T1. Initial implementation.** Implement REQ-001 to REQ-008.

**T2. Change request CR-1 (evolvability).** Implement the change in `experiment/tasks.md`
on top of your finished T1. In condition A this means: edit the spec and requirements,
regenerate, then update the logic.

## Order

You are one developer, so you will learn the domain during whichever condition comes first.
To make that visible rather than hidden: do **T1-B, then T1-A, then T2-A, then T2-B**, so each
condition goes first once. Report this learning effect as a limitation.

## Procedure for each task × condition

1. `git tag start-<task>-<cond>` (e.g. `start-T1-A`) and note the start time in `log.csv`.
2. Work until the first time you believe it is done. Run the tests once and record the result
   as the **first run** (`first_run_passed`, `first_run_failed`). Tag `first-<task>-<cond>`.
3. Continue until everything passes. Tag `done-<task>-<cond>` and note the end time.
4. Run `python experiment/measure.py <task> <cond>` and copy its numbers into `log.csv`.
5. Write two or three sentences in the `notes` column: where AI helped, where you had to step in.

Do not read the other condition's code while working, and don't change the tests. If a test
seems wrong, write it down and discuss it afterwards.

## Metrics

| Metric | Definition | Source |
|---|---|---|
| Lead time | Minutes from `start` to `done` (excluding breaks) | `log.csv` |
| AI attempts | Loop attempts until all gates passed (condition A) | `ai_attempts.csv` |
| Defects at first run | Acceptance tests failing at the `first` tag | `measure.py` |
| Rework | Lines added + removed between `first` and `done` | `measure.py` (git diff) |
| Hand-written lines | Lines of code you or the AI wrote (generated code excluded) | `measure.py` |
| Consistency | Contract violations found by `tests/test_contract.py` at `done` | `measure.py` |
| Mutation score (optional) | Share of injected bugs the acceptance tests catch, via `mutmut` | see README |

## Threats to validity (state these in the report)

- One developer and a small API: results show tendencies, not general proof.
- Learning effect between conditions (reduced by the order above, not removed).
- The acceptance tests were written together with the spec; a code-first team would normally
  write its own tests.
- Lead time is self-reported.
- A 7B local model is much weaker than the models used in industry.
