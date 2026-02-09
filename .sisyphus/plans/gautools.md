# GAUTools Project Plan

## Scope
- Build a Python CLI tool that logs into GSAU jwgl system and fetches:
  - Schedule by academic year/term
  - Grade list by year/term or all terms
  - Grade detail per course (from list)
- Support credential handling: prompt, env vars, config file (fallback chain)
- Output formats: table (console), JSON, CSV; optional file output
- Provide unit tests for parsing/formatting logic and integration test scaffold

## Tasks
- [x] 1. Establish project structure and dependencies
  - Create package layout under `gautools/`
  - Add `requirements.txt`, `.gitignore`, `config.example.ini`, `README.md`

- [x] 2. Implement core client (auth + session)
  - Extract login flow based on `gsau_schedule.py` and `gsau-login-schedule.md`
  - Support credential chain: prompt -> env -> config
  - Provide helper for authenticated requests

- [x] 3. Implement term and schedule APIs
  - Term list: `comm_cxXnmc` + `comm_cxXqjmc`
  - Schedule: `kbcx/xskbcx_cxXsgrkb.html` with `xnm/xqm`
  - Parse schedule to structured objects

- [x] 4. Implement grade list and grade detail
  - Grade list: `cjcx_cxDgXscj.html?doType=query&gnmkdm=N305005`
  - Grade detail: `cjcx_cxCjxq.html?gnmkdm=N305005`
  - Parse list JSON and detail HTML into structured objects

- [x] 5. Build CLI interface
  - Subcommands: `schedule`, `grades`, `grade-detail`, `terms`
  - Options: `--year`, `--term`, `--format`, `--output`
  - Config/env overrides and default behaviors

- [x] 6. Add tests and verification scripts
  - Unit tests for parsing/formatting
  - Integration test scaffold requiring credentials

## Verification
- `python -m pytest -q` (unit tests)
- Manual run examples:
  - `python cli.py schedule --year 2024 --term 2`
  - `python cli.py grades --year 2024 --term 2`
  - `python cli.py grade-detail --year 2024 --term 2 --jxb-id ...`
