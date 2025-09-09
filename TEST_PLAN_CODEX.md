# Autograder Test Plan (Codex)

This plan describes how to add comprehensive unit tests and mocked integration tests for the `autograder` repository. It prioritizes deterministic, offline tests with no network or real Git side-effects.

## Scope & Goals
- Coverage: target 80–90% on core modules in `actions/*` and CLI flow in `grade`.
- Determinism: tests run offline without network, GitHub, or Canvas access.
- Isolation: no writes outside temporary dirs; subprocesses and network fully mocked.
- Fidelity: validate happy paths, edge cases, and error handling across modules.

## Test Infrastructure
- Framework: `pytest` with `pytest-mock` (or `unittest.mock`).
- Structure:
  - `tests/conftest.py` for shared fixtures and global patches (e.g., block network by default).
  - `tests/fixtures/` for TOML, JSON, and tiny repo artifacts used by tests.
  - Per-module test files: `test_util.py`, `test_cmd.py`, `test_config.py`, `test_testcase.py`, `test_test_runner.py`, `test_git.py`, `test_github.py`, `test_canvas_server.py`, `test_dates.py`, `test_rollup.py`, `test_grade_cli.py`.
- Tools & techniques:
  - `tmp_path` for filesystem isolation.
  - `monkeypatch` and `mocker.patch` to stub env vars, subprocess, and network.
  - No real network: patch `requests` in `actions.server.Server`.
  - No real git: patch `actions.cmd.cmd_exec_rc`, `actions.cmd.cmd_exec_capture`, and `subprocess.Popen` when needed.

## Fixtures & Test Data
- `tests/fixtures/tests_repo/` (synthetic tests repo)
  - `proj/proj.toml` with several `[[tests]]` illustrating:
    - stdout vs file output (`output = 'stdout'` vs `output = 'file.txt'`).
    - `$project`, `$project_tests`, `$digital`, `$name` substitutions.
    - `case_sensitive = true` and default false cases.
    - `rubric` values for scoring.
  - `dates.toml` for `actions.dates` selection.
- `tests/fixtures/mini_repo/` (synthetic student repo)
  - `Makefile` with trivial `all` target; variants used in tests:
    - success build, missing Makefile, failing make.
  - Executable scripts that echo known strings; variants:
    - crash (exit nonzero), timeout (simulated), noisy output (to test `strip_output`).
- Rollup inputs:
  - Multiple JSON files representing `grade class --by-date` outputs across milestones.

Reusable fixtures (in `conftest.py`):
- `fake_args(...)`: construct `actions.config.Args` by monkeypatching `sys.argv` to exercise CLI defaults and flags.
- `fake_config(tmp_path)`: in-memory/defaulted `Config` object (avoid reading user files) for commands that require it.
- `tests_repo(tmp_path)`: materialize synthetic tests repo and set `Test.tests_path` to it.
- `mini_repo(tmp_path)`: create a tiny buildable repo; yield its path for build and execution tests.
- `block_network` (autouse): patch `requests` in `actions.server.Server` to raise if used unintentionally.

## Unit Tests: util, config, cmd
- `actions.util`:
  - `project_from_cwd`: parse repo folder names with and without `-user` suffix.
  - `load_toml`: returns dict on success, `{}` on missing file, and calls `fatal()` on parse error (assert `SystemExit`).
  - `format_pass_fail` alignment and `failed()` logic.
  - `SafeConfig.safe_update`: updates only known keys; unknown key triggers `fatal()` (assert `SystemExit`).
  - Color print helpers don’t crash (no strict color assertions).
- `actions.config`:
  - `Config.get_path()` precedence: env `GRADE_CONFIG_DIR` over parent traversal over default `~/.config/grade`.
  - `Config.write_default_tables()`: produces commented TOML entries.
  - `Args.from_cmdline()`: via `sys.argv` monkeypatch; validates defaults for `-p`, `-v`, `-vv`, `--by-date`, etc.
- `actions.cmd`:
  - `cmd_exec_capture` and `cmd_exec_rc` happy path using a harmless command; use `shell=False` and a short timeout.
  - Timeout path: patch `subprocess.Popen` to simulate blocking; assert `TimeoutExpired` handling and cleanup.
  - Output limit path: simulate stream with repeated data causing `OutputLimitExceeded` (or early termination) as implemented.

## Unit Tests: TestCase & Test runner
- `TestCase.init_cmd_line`: verify `$project`, `$project_tests`, `$digital`, `$name` substitutions.
- `TestCase.get_actual`:
  - stdout capture vs file output capture; `capture_stderr=True/False` behavior.
  - `strip_output` removal when configured.
  - `build='go'` path: feed JSON lines exercising `get_actual_go()` including "pass" shortcut and "warning: no tests to run".
- `TestCase.match_expected`:
  - Case-insensitive and case-sensitive comparisons; per-line trimming.
  - Verbose diff path: guard via `args.verbose/very_verbose` to avoid brittle output checks (smoke asserts only).
- `Test.build`:
  - `build='none'` no-op.
  - Make success/failure via patched `cmd_exec_rc`; missing Makefile and missing repo path handling.
  - `build='go'` branch (patched to avoid invoking go toolchain).
- `Test` scoring/formatting:
  - `total_score`, `total_rubric`, `make_earned_avail`, `make_comment` accumulation including `build_err` and `test_err` fields.
  - `run_test_cases` filtering by `--test-name`.
  - `print_histogram` executes and emits stable output (basic smoke test).

## Unit Tests: Git, Github, Canvas/Server
- `Git.make_remote_path`: ssh vs https URL formats; unknown credentials fatal.
- `Git.get_default_branch`: patch `subprocess.Popen` pipeline to return a line with the HEAD branch; empty output raises `GitNoBranches`.
- `Git.get_commit_hash`: patch `cmd_exec_capture` to return commit+date lines; verify date time suffixing; empty output raises `GitNoCommits`.
- `Git.get_url_for_hash`: patch `cmd_exec_capture` to return a short hash; on exception, comment remains unchanged.
- `Github`:
  - Header and URL builders.
  - `get_first_artifact_for_repo`: patch `Server.get_url` to return artifacts JSON; empty or exceptions are warned and return `{}`.
  - `get_artifact_results`: feed a fake ZIP with `grade-results.json`; parse and convert `grade` to float; warn paths on errors.
  - `get_action_results`: aggregates into `repo_result` using above helpers.
- `Server`:
  - `make_url`, `add_auth_header` basics.
  - `get_url` content-type handling: JSON vs ZIP, with fake `requests.Response` objects; ensure warn+raise on HTTP errors.
  - `put_url` returns True/False based on status code.

## Unit Tests: Dates & Rollup
- `Dates.from_path`: load from synthetic `dates.toml`; project scoping; error on missing project table.
- `Dates.select_date`: patch `TerminalMenu.show` to return index and `None` (cancel) paths.
- `rollup.rollup`:
  - Provide multiple per-suffix JSON inputs with varying scores to validate the rolling formula and appended comments.
  - Verify output file `<project>-rollup.json` exists and contains expected rolled results.

## Mocked CLI Integration Tests
- CLI routing (`grade`):
  - Default project from cwd vs `-p` override.
  - `action=test`: run end-to-end with synthetic tests repo and student repo; patch `cmd_exec_*` to deterministic outputs; assert pass/fail tokens and final score print.
  - `action=class`: two repos; patch `Test.test` to return results with `score` and `comment`; histogram printed and JSON written; `--by-date` path with patched `Dates.select_date`.
  - `action=clone`/`pull`: patch `Git.clone`/`Git.pull`; ensure called per student in config and respects `-s` override. Exercise CanvasMapper fallback error message path without reading real CSV (patch to provide list).
  - `--exec`: ensure `cmd_exec_capture` invoked with provided shell command in each repo.

## Coverage & CI
- Local dev dependencies (do not add to runtime requirements):
  - `pytest`, `pytest-mock`, `pytest-cov`.
- Example commands:
  - `pytest -q` for quick run.
  - `pytest --cov=actions --cov-report=term-missing` to see coverage.
- Optional GitHub Actions workflow:
  - Python 3.10–3.13 matrix, install dev deps, run pytest with coverage threshold `--cov-fail-under=85`.

## How To Run Locally
1. Create a virtual environment and install dev deps:
   - `python3 -m venv .venv && source .venv/bin/activate`
   - `pip install -U pip pytest pytest-mock pytest-cov`
2. Run tests: `pytest -q`
3. With coverage: `pytest --cov=actions --cov-report=term-missing`

## Non‑Goals
- Hitting real GitHub/Canvas APIs or cloning/pulling actual repos.
- Testing the Digital GUI; we only substitute `$digital` and validate command-line construction.

## Notes & Risks
- `actions.cmd` uses low-level stream reads with `.peek()` and `select`; prefer mocking `subprocess.Popen` and its file descriptor to avoid flakiness.
- `fatal()` calls `sys.exit(-1)`; tests should assert `SystemExit` rather than capturing printed color output.
- `simple-term-menu` usage is patched in tests to avoid TTY interaction.
- When diff output is asserted, keep checks coarse (presence of headers) to avoid brittleness across platforms.

