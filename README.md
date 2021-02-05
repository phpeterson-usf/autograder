# autograder
`grade` is a tool for Computer Science students and instructors to test student projects for correctness. Its features include:
1. Clone all student repos based on a list of Github IDs
1. Build all student repos using `make`
1. Run all student repos against instructor-provided input files
1. Score actual output vs. expected using an instructor-provided rubric.
1. Integration with the [Digital](https://github.com/hneemann/Digital) circuit simulation tool

## Requirements
1. Requires python3 and pip3. Python 3.7.3 is pre-installed on Raspberry Pi OS.
    ```
    $ sudo apt install python3-pip
    ```
1. Requires [TOML](https://toml.io/en/) python module
    ```
    $ pip3 install toml
    ```

## Installation
1. Clone the `autograder` repo
    ```
    $ cd ~
    $ git clone git@github.com:/phpeterson-usf/autograder.git
    ```
1. Add the directory to your path in `~/.bashrc`
    ```
    export PATH = ~/autograder/:$PATH
    ```
1. Clone your class's tests repo. Use the right one for your class - these are just examples.
    ```
    $ cd ~
    $ git clone git@github.com:/cs315-21s/tests.git
    $ git clone git@github.com:/USF-CS631-S21/tests.git
    ``` 
1. Run the `grade` script once and it will create a config file in `~/.config/grade`. Edit this so it contains the following pieces of information:
   1. The authentication you use for GitHub: ssh or http
   1. The Github Classroom organization for your class
   1. The path to your tests repo
        ```
        credentials = "ssh"
        testpath = "/home/pi/tests"
        ```

## Usage for Students
1. You can test a project in the current directory like this
    ```
    $ cd ~/project02-phpeterson-usf
    $ grade test --project project02
    ```

## Usage for Instructors
1. Add your Github Classroom organization and a list of students to your `~/.config/grade/config.toml`
    ```
    org = "cs315-21s"
    students = [
        "phpeterson-usf",
        "gdbenson",
    ]
    ```
1. You can clone all of your students repos to your machine. `grade` will create `./github.com/` in the current working directory, with subdirectories for your organization and student repos
    ```
    $ grade clone
    github.com/cs315-21s/project02-phpeterson-usf
    github.com/cs315-21s/project02-gdbenson
    ```
1.  After developing test cases for your projects (see below), you can test all of your students' repos in batch
    ```
    $ grade class
    project02-phpeterson-usf 01 02 10/10
    project02-gdbenson       01 02 10/10
    ```
1. Each test case can pass or fail. The score is shown as the total earned/total available, based on the `rubric` field in each test case

## Test Cases
1. Instructors must create their own repo for the test cases for the class projects. Students will clone and pull this repo. We create this repo in the Github Classroom Organization, but that's up to you.
1. Test cases for each project are expressed in TOML, as you can see in the `example_tests/` directory here
1. Test case inputs are a list of strings for each command-line flag and value. The keyword `$project` will be substituted for
the name of your project. 
    ```
    $ cat project02.toml
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
    ```
    [[tests]]
    input = ["python3", "$project.py"]
    ```
1. Test cases can have input files in your `tests` repo using the keyword `$project_tests`, which will be 
substituted for `$testspath/$project/`. In this example, substitution gives the input file as `$testspath/project02/testinput.txt`
    ```
    [[tests]]
    name = "03"
    input = ["./$project", "$project_tests/testinput.txt"]
    ```
1. Test case output can be recorded from `stdout` or from a file. If `output` is not given, Autograder defaults to `stdout`
    ```
    [[tests]]
    name = "04"
    output = "04.txt"
    input = ["./$project", "-o", "04.txt"]
    ```

## Command Line Parameters
1. `grade` supports these parameters, which can be given on the command line, or in `~/.config/grade/config.toml`, for less typing. 
1. The syntax in `config.toml` just uses the name, without dashes, as shown at the top of this README
1. The command-line format is argparse-style, with no "=". These two commands are equivalent:
    ```
    $ cd ~/project02-jsmith
    $ grade test -p project02
    $ grade test --project project02
    ```
1. Parameters given on the command line override those given in `config.toml`
* `-c/--credentials` [https | ssh] https is the default
* `-d/--digital` is the path to Digital's JAR file
* `-i/--ioprint` prints inputs and outputs to help write project specs
* `-n/--name` runs one named test case, rather than all of them
* `-o/--org` is the Github Classroom Organization 
* `-p/--project` is the name of the project, which is substituted into repo names and test case inputs
* `-s/--students` is a list of student Github IDs (no punctuation needed)
* `-v/--verbose` shows some of what autograder is doing

## Using Digital
1. [Digital](https://github.com/hneemann/Digital) has test case components which can test a circuit using pre-defined inputs and outputs. See Digital's documentation for scripted testing examples.
1. `grade` leverages its ability to loop over the student repos, using Java and Digital's test case components, looking
for a passing report from Digital
1. Examples of Digital test cases combined with autograder test cases are available [here](https://github.com/phpeterson-usf/autograder/tree/main/tests/project06)
1. `grade` needs to know where Digital's JAR file lives. There is a configuration for that path in `config.toml`, in your platform's native format
    ```
    digital = "/home/me/Digital/digital.jar"
    ```
