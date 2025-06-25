# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

### Development Commands
- **Install dependencies**: `pip3 install -r requirements.txt` or use `uv` package manager
- **Run autograder**: `./grade <action> [options]` or `python3 grade <action> [options]`
- **Common actions**:
  - `grade test` - Test current directory
  - `grade clone -p <project>` - Clone student repos
  - `grade class -p <project>` - Test all student repos
  - `grade upload -p <project>` - Upload results to Canvas

### Testing
- **Run specific test**: `grade test -n <test_name>`
- **Verbose output**: `grade test -v` (shows expected/actual for failures)
- **Very verbose**: `grade test -vv` (shows all expected/actual)

## Architecture

### Core Components
The autograder follows a modular architecture with distinct responsibilities:

1. **Entry Point** (`grade`): Orchestrates all operations through a CLI interface
2. **Configuration System** (`actions/config.py`): 
   - Hierarchical config loading: env var → local config.toml → ~/.config/grade/config.toml
   - Auto-creates default config if missing
3. **Test Engine** (`actions/test.py`):
   - Executes test cases defined in TOML format
   - Handles scoring, timeouts (60s default), and output limits (10KB)
   - Supports stdout/file output comparison
4. **Git Integration** (`actions/git.py`): Manages clone/pull operations with date-based checkout
5. **Canvas Integration** (`actions/canvas.py`): Uploads grades via REST API
6. **GitHub Integration** (`actions/github.py`): Fetches GitHub Actions results

### Test Case Format
Test cases are defined in TOML files with this structure:
```toml
[[tests]]
name = "test_name"
input = ["./\$project", "arg1", "arg2"]  # \$project substituted with project name
expected = "expected output"
rubric = 10  # points for this test
output = "file.txt"  # optional: check file instead of stdout
case_sensitive = false  # default
```

### Key Design Patterns
- **Batch Operations**: Processes multiple student repos in parallel
- **Result Persistence**: Saves test results as JSON for later Canvas upload
- **Variable Substitution**: `$project` and `$project_tests` in test inputs
- **Error Resilience**: Graceful handling of missing repos, timeouts, and build failures