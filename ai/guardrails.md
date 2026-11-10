# Guardrails for AI-written business logic

These rules are sent to the model with every request. The ones marked (checked) are also
enforced by `gates/check_guardrails.py` or the tests, so breaking them fails the build.

1. Write only the file `src/logic/service.py`. Never edit anything under `src/generated/`. (checked)
2. Define `class VoucherService(VoucherServiceBase)` and implement every method of the
   generated interface, with the same parameter names. (checked)
3. Every method returns a tuple `(status_code, payload_dict)`. Use only the status codes
   listed in that method's docstring, and payloads with exactly the fields of the named
   schema. (checked at build time and at runtime)
4. Error payloads are `{"code": ..., "message": ...}` using the codes from REQ-008. (checked)
5. The generated routes already validate request bodies against the schema (types, ranges,
   required and unknown fields), so do not repeat those checks. They do NOT check `format`
   (for example `date-time`); validate formats in the logic and return 422 VALIDATION_ERROR.
6. Keep all state in memory on the instance (for example dictionaries created in `__init__`).
7. Imports allowed: `uuid`, `secrets`, `threading`, `dataclasses`, `typing`, `copy`,
   `datetime`, `time` and `src.generated.service_base`. No file, network or process access, no `print`. (checked)
8. Never return internal objects directly; return copies so callers cannot change stored state.
9. Answer with one Python code block containing the complete file and nothing else.
