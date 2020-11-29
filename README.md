# autograder
1. Clone and build repos from Github Classroom
2. Run test cases vs. expected output
3. Generate a score based on a rubric for each test case
4. Automated testing using the [Digital](https://github.com/hneemann/Digital) circuit simulation tool

## Requirements
1. Requires python3
1. Requires toml python module

## Usage for students
You will need a file called `config.toml` which contains the Github Classroom organization
name and the project name for the current project want to test. 
<pre><code>$ cd ~
$ git clone https://github.com/phpeterson-usf/autograder.git
$ cd autograder
$ cat > config.toml
org = "cs-315-03-20f"
project = "project02"
^D
</code></pre>
For less typing you can make the autograder python program executable:
<pre><code>$ chmod +x ag.py
</code></pre>
You can test your project like this:
<pre><code>$ ./ag.py test --local ~/project02-jsmith
</code></pre>
## Usage for instructors
1. Test cases for each project are expressed in TOML, as you can see in the `tests/` directory
1. Conventionally, the executable name and the project name are the same, 
as shown below.
1. Test case inputs are a list of strings for each command-line flag and value, since
that's how python subprocess takes arguments. The keyword `$project` will be substituted for
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
        input = ["java", "-cp", "$project.jar"]
        </code></pre>
1. Test cases can have input files in your tests/ directory using the keyword `$project_tests`, which will be 
substituted for `tests/$project/`. In this example, substitution gives the input file as `tests/project02/testinput.txt`
        <pre><code>[[tests]]
        name = "03"
        input = ["./$project", "$project_tests/testinput.txt"]
        </code></pre>
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
1. Now autograder can loop over the list of students to clone and test:
        <pre><code>$ ./ag clone
        $ ./ag.py test
        project02-phpeterson-usf 01 02 10/10
        project02-gdbenson       01 02 10/10
        </code></pre>

## Using Digital
1. In our course, we teach circuit simulation using a Java-based
simulation tool called [Digital](https://github.com/hneemann/Digital)
1. Digital has test case components which can test a circuit
using pre-defined inputs and outputs. See Digital's documentation. 
1. Autograder leverages its ability to loop over the student repos, using Java and Digital's test case components, looking
for a passing report from Digital
1. Examples of Digital test cases combined with autograder test cases are available [here](https://github.com/phpeterson-usf/autograder/tree/main/tests/project06)
1. Since autograder needs to know where Digital's JAR file lives,
there is a configuration for that path in `config.toml`, in your platform's native format
        <pre><code>digital = "/home/me/Digital/digital.jar"
        </code></pre>

## Autograder config/command line flags
I intended autograder to be simple, but along the way of supporting the use cases I needed, I added these flags, which can be given on the command line, or in `config.toml`
* `-c/--credentials` [https | ssh] https is the default
* `-d/--digital` is the path to Digital's JAR file
* `-l/--local` is the path to the local repo to test
* `-o/--org` is the Github Classroom Organization 
* `-p/--project` is the name of the project, which is substituted into repo names and test case inputs
* `-s/--students` is a list of student Github IDs (no punctuation needed)
* `-v/--verbose` shows some of what autograder is doing
