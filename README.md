# autograder
Autograder is a tool for Computer Science students and instructors to test student projects for correctness. Its features include:
1. Clone all student repos based on a list of Github IDs
1. Build all student repos using `make`
1. Run all student repos against instructor-provided input files
1. Score actual output vs. expected using an instructor-provided rubric.
1. Integration with the [Digital](https://github.com/hneemann/Digital) circuit simulation tool

## Requirements
1. Requires python3 
        <pre><code>$ sudo apt install python3.8 python3-pip</pre></code>
1. Requires [TOML](https://toml.io/en/) python module
        <pre><code>$ pip3 install toml</code></pre>

## Basic Usage
1. `clone` and `test` are the basic actions Autograder can perform. One of those actions must be provided on the command line.
1. You will need a file called `config.toml` which contains the Github Classroom organization
name and the project name for the current project want to test. 
        <pre><code>$ cd ~
        $ git clone https://github.com/phpeterson-usf/autograder.git
        $ cd autograder
        $ cat > config.toml
        org = "cs-315-03-20f"
        project = "project02"
        ^D
        </code></pre>
1. For less typing you can make the autograder python program executable
        <pre><code>$ chmod +x ag.py
        </code></pre>
1. You can test your project like this
        <pre><code>$ ./ag.py test --local ~/project02-jsmith
        </code></pre>
1. Each test case can pass or fail. The score is shown as the total earned/total available, based on the `rubric` field in each test case

## Test Cases
1. Test cases for each project are expressed in TOML, as you can see in the `tests/` directory
1. Test case inputs are a list of strings for each command-line flag and value. The keyword `$project` will be substituted for
the name of your project. 
	<pre><code> $ cat project02.toml
    [[tests]]
    name = "01"
    input = ["./$project", "-e", "1 + 1"]
    expected = "2"
    rubric = 5
    
    [[tests]]
    name = "02"
    input = ["./$project", "-e", "10", "-b", "16"]
    expected = "0x0000000A"
    rubric = 5</code></pre>
1. Note that this usage of `$project` is flexible enough for projects which are run using an interpreter like Java or Python
        <pre><code>[[tests]]
        input = ["python3", "$project.py"]
        </code></pre>
1. Test cases can have input files in your `tests/` directory using the keyword `$project_tests`, which will be 
substituted for `tests/$project/`. In this example, substitution gives the input file as `tests/project02/testinput.txt`
        <pre><code>[[tests]]
        name = "03"
        input = ["./$project", "$project_tests/testinput.txt"]
        </code></pre>
1. Test case output can be recorded from `stdout` or from a file. If `output` is not given, Autograder defaults to `stdout`
        <pre><code>[[tests]]
        name = "04"
        output = "04.txt"
        input = ["./$project", "-o", "04.txt"]
        </code></pre>

## Looping and Scoring
 1. You can add a list of students Github IDs to `config.toml`
        <pre><code>$ cat config.toml
        credentials="https"
        org = cs-315-03-20f"
        project = "project02"
        students = [
            "phpeterson-usf",
            "gdbenson",
        ]
        </code></pre>
1. Autograder can loop over the list of students to clone and test (assuming parameters are given in `config.toml`)
        <pre><code>$ ./ag clone
        $ ./ag.py test
        project02-phpeterson-usf 01 02 10/10
        project02-gdbenson       01 02 10/10
        </code></pre>

## Parameters
1. Autograder supports these parameters, which can be given on the command line, or in `config.toml`, for less typing. 
1. The syntax in `config.toml` just uses the name, without dashes, as shown at the top of this README
1. The command-line format is argparse-style, with no "="
        <pre><code>$ ./ag.py test -p project02 -l ~/project02-jsmith</code></pre>
1. Parameters given on the command line override those given in `config.toml`
* `-c/--credentials` [https | ssh] https is the default
* `-d/--digital` is the path to Digital's JAR file
* `-l/--local` is the path to the local repo to test
* `-o/--org` is the Github Classroom Organization 
* `-p/--project` is the name of the project, which is substituted into repo names and test case inputs
* `-s/--students` is a list of student Github IDs (no punctuation needed)
* `-v/--verbose` shows some of what autograder is doing

## Using Digital
1. [Digital](https://github.com/hneemann/Digital) has test case components which can test a circuit using pre-defined inputs and outputs. See Digital's documentation for scripted testing examples.
1. Autograder leverages its ability to loop over the student repos, using Java and Digital's test case components, looking
for a passing report from Digital
1. Examples of Digital test cases combined with autograder test cases are available [here](https://github.com/phpeterson-usf/autograder/tree/main/tests/project06)
1. Autograder needs to know where Digital's JAR file lives. There is a configuration for that path in `config.toml`, in your platform's native format
        <pre><code>digital = "/home/me/Digital/digital.jar"
        </code></pre>
