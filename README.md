# autograder
`grade` is a tool for Computer Science students and instructors to test student projects for correctness. Its features include:
1. Clone all student repos based on a list of Github IDs
1. Build all student repos using `make`
1. Run all student repos against instructor-provided input files
1. Score actual output vs. expected using an instructor-provided rubric.
1. Integration with the [Digital](https://github.com/hneemann/Digital) circuit simulation tool
1. Automated upload of results to [Canvas](https://www.instructure.com/)

## Requirements

### [uv](https://docs.astral.sh/uv/)

- Cargo

```sh
$ cargo install --git https://github.com/astral-sh/uv uv
```

- Homebrew

``` sh
$ brew install uv
```

- Nix

On NixOS:

```sh
$ nix-env -iA nixos.uv
```

On Non NixOS:

```sh
$ # without flakes:
nix-env -iA nixpkgs.uv
# with flakes:
nix profile install nixpkgs#uv
```

## Installation

1. Install `grade` executable to your system `PATH` using `uv`.

    ```
    $ uv tool install git+https://github.com/phpeterson-usf/autograder
    ```

1. Clone your class's tests repo. Use the right one for your class - these are just examples.

    ```
    $ cd ~
    $ git clone git@github.com:/cs315-21s/tests.git
    $ git clone git@github.com:/USF-CS631-S21/tests.git
    ``` 

---
## Usage for Students
1. You can test a project in the current directory like this
    ```
    $ cd ~/project02-phpeterson-usf
    $ grade test
    ```
    note that `grade` will infer the project name based on your current directory.
1. `grade` will create a config file in `~/.config/grade/config.toml` containing its default settings.
You do not need to modify this file unless you need non-default settings
1. Example settings
    1. `grade` assumes that you authenticate to Github using `ssh`. If you authenticate to github using http, you
    could change `config.toml` like this
        ```toml
        [Git]
        credentials = "https"  # default is"ssh"
        ```
    1. `grade` assumes that test cases are in `~/tests/`. If you put the your test case repo in a different directory,
    you could change `config.toml` to point to that directory
        ```toml
        [Test]
        tests_path = "~/myclass/tests"  # default is "~/tests"
        ```
    
---
## Usage for Instructors
1. Add your Github Classroom organization and a list of students to `~/.config/grade/config.toml`
    ```
    [Git]
    org = "cs315-f22"

    [Config]
    students = [
        "phpeterson-usf",
        "gdbenson",
    ]
    ```
1. You can clone all of your students' repos to your machine. `grade` will create a directory for each repo in your current working directory
    ```
    $ grade clone -p project02
    ./project02-phpeterson-usf
    ./project02-gdbenson
    ```
1. `grade clone` can take a student GitHub username, or several of them
    ```
    $ grade clone -p project02 -s phpeterson-usf gdbenson
    ```
1. `grade clone` can accept a date, or date and time, for your project deadline
    ```
    $ grade clone -p project02 --date '2021-10-14'
    $ grade clone -p project02 --date '2021-10-14 08:00:00'
    ```
    Notes:
    1. If no time is given, the script assumes midnight `00:00:00`
    1. The script uses `git rev-list` to find the commit hash of the last commit on the default branch ('main' or 'master') before that date
    1. The script uses `git checkout` to checkout the repo as of that hash. Keep in mind this leaves the repo in a "detached HEAD" state
    1. If you want to checkout the tip of the default branch again, you can use `grade pull`
1.  After developing test cases for your projects (see below), you can test all of your students' repos in batch. Passing test cases are shown in green with a '+' and failing test cases are shown in red with a '-'
    ```
    $ grade class -p project02
    project02-phpeterson-usf 01- 02+  5/10
    project02-gdbenson       01+ 02+  10/10
    ```
1. Each test case can pass or fail. The score is shown as the total earned/total available, based on the `rubric` field in each test case
1. Optional config: If you want to put `config.toml` into another location (perhaps a per-semester directory), you can use the shell environment variable
`GRADE_CONFIG_DIR` which causes the grade script to look for `config.toml` in the named directory. For example, `~/.bashrc` might contain
`export GRADE_CONFIG_DIR=~/cs521-s24` or whatever directory is useful to you.
1. Optional config: If you need more than one config file at a time, you may create a `config.toml` file in any 
directory under your home directory, and `grade` will prefer that to `~/.config/grade/`

## Test Cases
1. Instructors must create their own repo for the test cases for the class projects. Students will clone and pull this repo. We create this repo in the Github Classroom Organization, but that's up to you.
1. Test cases for each project are expressed in TOML 
1. Test case inputs are a list of strings for each command-line flag and value. The keyword `$project` will be substituted for the name of your project. 
    ```toml
    [[tests]]
    name = "01"
    input = ["./$project", "-e", "1 + 1"]
    expected = "2"
    rubric = 5
    
    [[tests]]
    name = "02"
    input = ["./$project", "-e", "10", "-b", "16"]
    expected = "0x0000000A"
    rubric = 5
    ```
1. Note that this usage of `$project` is flexible enough for projects which are run using an interpreter like Java or Python
    ```toml
    [[tests]]
    input = ["python3", "$project.py"]
    ```

### Input and Output Variations
1. Test cases can have input files in your `tests` repo using the keyword `$project_tests`, which will be 
substituted for `$testspath/$project/`. In this example, substitution gives the input file as `$testspath/project02/testinput.txt`
    ```toml
    [[tests]]
    name = "03"
    input = ["./$project", "$project_tests/testinput.txt"]
    ```
1. Test case output can be recorded from `stdout` or from a file. In this example, the contents of the file `04.txt` will be compared to the `expected` field of the test case. 
    ```toml
    [[tests]]
    name = "04"
    output = "04.txt"
    input = ["./$project", "-o", "04.txt"]
    ```
    If `output` is not given, `grade` defaults to `stdout`
1. Comparing expected output with actual output is case-insentitive by default. If you want case-sensitive comparison, you can set that in a test case
    ```toml
    [[tests]]
    name = to_upper
    input = input = ["./$project", "foObAr1"]
    expected = "FOOBAR1"
    case_sensitive = true
    ```
1. Autograder assumes that the student repo will be the working directory for testing. If your project requires a subdirectory within all student repos, you can add that in the `[project]` settings in the test case TOML file
    ```toml
    [project]
    subdir = "xv6"
    ```
### Infinite Loops
1. Autograder will wait for 60 seconds for a program to finish before concluding that the program is in an infinite loop and killing it. If you need to wait longer than 60 seconds, you can change that setting in the `[project]` section of the test case TOML file
    ```toml
    [project]
    timeout = 120  # two minutes
    ```
1. Autograder will collect at most 10,000 bytes of output before concluding that the program is in an infinite loop and killing it. 

## Command Line Parameters
1. `grade` supports these command-line parameters
* `-d/--date` is the date to use for grade clone
* `-e/--exec` provide commands to execute (e.g. `git pull; make clean`)
* `-g/--github-action` tells `grade class` to get the test result from `api.github.com` rather than local testing
* `-n/--name` with `grade test` runs one named test case, rather than all of them
* `-p/--project` is the name of the project, which is substituted into repo names and test case inputs
* `-v/--verbose` shows expected and actual for failing test cases
* `-vv/--very-verbose` shows expected and actual for all test cases

    The command-line format is `argparse`-style, with no "=". These two commands are equivalent:
    ```
    $ cd ~/project02-jsmith
    $ grade test -p project02
    $ grade test --project project02
    ```

## Using Canvas (instructors only)
1. In order to map GitHub usernames to Canvas login IDs, you need to provide a mapping file. 
We ask students to fill out a Google Form which produces a Google Sheets spreadsheet. If you
download that spreadsheet to a local CSV file, you can give the mapping configuration in `~/.config/grade/config.toml`
    ```toml
    [CanvasMapper]
    map_path = "~/github-to-canvas.csv"  # CSV file which maps GitHub username to Canvas SIS Login ID
    github_col_name = "GitHub"  # Name of the CSV column which contains the GitHub username
    login_col_name = "SIS Login ID"  # Name of the CSV column which contains the Canvas SIS Login ID
    ```
1. After you run `grade class -p lab01` the test results will be stored in a JSON file, e.g. `./lab01.json`
1. You can subsequently run `grade upload -p lab01` to upload the results to [Canvas](https://canvas.instructure.com/doc/api/index.html)
1. The JSON file contains the aggregate score for the repo (e.g. 80 out of 100 pts) and a submission comment showing which tests passed and failed. The comment will also be uploaded.
1. The name you use for the `project` in `grade` must match the name of the assignment in Canvas, case-sensitively. 
1. Since the Canvas REST API for submissions does not know about assignment groups, I recommend you create the assignment in Canvas before running `grade upload`. Otherwise Canvas will create a new assignment outside your structure for assignment groups
1. `grade upload` manipulates only the named Canvas assignment. It does not mimic the uploading of CSV files shown in the Canvas web UI.
1. In order to upload, you must add these attributes to the `[Canvas]` section in `~/.config/grade/config.toml`
    ```toml
    [Canvas]
    host_name = "canvas.instructure.com"  # your institution may have a test instance of Canvas
    access_token = "xxx"  # create an access token in Profile | Settings in Canvas
    course_name = "Your long course name"  # e.g. 'Computer Architecture - 01 (Spring 2022)'
    ```
4. If Canvas isn't working for you, try the `-v` command-line flag, which will print the results of each Canvas REST API

## Using Digital
1. [Digital](https://github.com/hneemann/Digital) has test case components which can test a circuit using pre-defined inputs and outputs. See Digital's documentation for scripted testing examples.
1. `grade` leverages its ability to loop over the student repos, calling Java on the command line to use Digital's test case components. Example test case:
    ```toml
    [project]
    build = "none"
    strip_output = """
    Use default settings!
    """

    [[tests]]
    name = "1-bit-full-adder"
    input = ["java", "-cp", "$digital", "CLI", "test", "1-bit-full-adder.dig", "-tests", "$project_tests/1bfa_test.dig"]
    expected = """
    1bfa_test: passed
    """
    rubric = 1
    ```
1. `grade` assumes that the path to the Digital JAR file is `~/Digital/Digital.jar`. If you need a different setting, you can change it in the `[Test]` section of `~/.config/grade/config.toml`:
    ```toml
    [Test]
    digital_path = "~/myclass/Digital/Digital.jar"
    ```
## Using GitHub Actions
1. If you use GitHub Actions to do the testing, autograder can download the results for each student repo and upload the class results to Canvas
1. If you use `grade class` with the flag `-g/--github-action`, autograder can use the GitHub REST API to download the results into a JSON file
    ```sh
    grade class -p project01 -g
    ```
1. Once we have the class results in a JSON file, you can upload them to Canvas
    ```
    grade upload -p project01
    ```
1. To configure autograder to download the results of GitHub Actions, edit `~/.config/grade/config.toml` to include these settings
    ```toml
    [Github]
    access_token = "xxx" # create in your Github settings | Developer Settings | Tokens (classic)  
    ```

## Late Grading (instructors only)
1. autograder has an algorithm for grading late work: full credit for work done by the due date, for work handed in X days late,
discount the improvement (new score - old score) by Y%. 
1. The late milestones are specified in a file called `dates.toml` which lives in your `tests` repo and is formatted like this:
    ```
    [project04]

    [[project04.dates]]
    suffix = "due"
    date = "2025-03-18"
    percentage = 1.0

    [[project04.dates]]
    suffix = "Late1wk"
    date = "2025-03-25"
    percentage = 0.5
    ```
1. When you `grade clone` or `grade class` you can use the `-d`/`--by-date` flag to choose which milestone  you want to work on
1. Each invocation of `grade class -d` will generate a JSON score file, e.g. `project04-due.json`
1. The percentage deduction is done with `grade rollup -d` which applies the deductions and generates `project04-rollup.json`
1. Use `grade upload -d` to choose the JSON file to upload to Canvas, perhaps always the rolled-up grades.
