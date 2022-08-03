# autograder
`grade` is a tool for Computer Science students and instructors to test student projects for correctness. Its features include:
1. Clone all student repos based on a list of Github IDs
1. Build all student repos using `make`
1. Run all student repos against instructor-provided input files
1. Score actual output vs. expected using an instructor-provided rubric.
1. Integration with the [Digital](https://github.com/hneemann/Digital) circuit simulation tool
1. Automated upload of results to [Canvas](https://www.instructure.com/)

## Requirements
1. Requires python3 and pip3
    ```sh
    $ sudo apt install python3-pip
    ```

## Installation
1. Clone the `autograder` repo
    ```sh
    $ cd ~
    $ git clone git@github.com:/phpeterson-usf/autograder.git
    $ cd autograder
    ```
1. Install python modules (mainly `tomlkit` and `requests`)
    ```sh
    $ pip3 install -r requirements.txt
    ```
1. Edit `~/.bash_profile` (on Linux or Git Bash on Windows) or `~/.zshrc` (on macOS) to include the path to `grade`
    ```
    export PATH=~/autograder:$PATH
    ```
1. Use the `source` command on that file to update your environment 
    ```sh
    $ source ~/.zshrc
    ```
1. Clone your class's tests repo. Use the right one for your class - these are just examples.
    ```
    $ cd ~
    $ git clone git@github.com:/cs315-21s/tests.git
    $ git clone git@github.com:/USF-CS631-S21/tests.git
    ``` 
---
## Usage for Students
1. By default, `grade` assumes that you authenticate to Github using `ssh` and test cases are in `~/tests`. If you need different settings, you can edit the config file: `~/.config/grade/config.toml`:
    ```toml
    [Git]
    credentials = "https"  # default is"ssh"

    [Test]
    tests_path = "~/myclass/tests"  # default is "~/tests"
    ```
1. You can test a project in the current directory like this
    ```
    $ cd ~/project02-phpeterson-usf
    $ grade test --project project02
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

## Command Line Parameters
1. `grade` supports these command-line parameters
* `-d/--date` is the date to use for grade clone
* `-e/--exec` provide commands to execute (e.g. `git pull; make clean`)
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
