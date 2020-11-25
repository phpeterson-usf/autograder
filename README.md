# autograder
1. Clone and build repos from Github Classroom. 
2. Run test cases vs. expected output
3. Generate a score based on a rubric for each test case

## Requirements
1. Requires python3
1. Requires toml python module

## Usage for students
You will need a file called config.toml which contains the Github Classroom organization
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
<pre><code>$ ./ag test --local ~/project02-jsmith
</code></pre>
Autograder can also clone your repo so you can check to make sure you didn't forget to
commit something. If you use ssh to connect to Github, you should add that to config.toml
<pre><code>credentials = "ssh"
</code></pre>
## Usage for instructors
1. Test cases for each project are expressed in TOML, as you can see in the `tests/` directory
1. Test case inputs are a list of strings for each command-line flag and value, since
that's how python subprocess takes arguments. Maybe there's a better way
	<pre><code> $ cat project02.toml
        [[tests]]
        name = "01"
        input = ["-e", "1 + 1"]
        expected = "2"
        rubric = 5
        
        [[tests]]
        name = "02"
        input = ["-e", "10", "-b", "16"]
        expected = "0x0000000A"
        rubric = 5</code></pre>
1. You can add a list of students Github IDs to config.toml 
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
        <pre><code>pi@raspberrypi:~/autograder $ ./ag clone
        pi@raspberrypi:~/autograder $ ./ag test
        project02-phpeterson-usf 01 02 10/10
        project02-gdbenson       01 02 10/10
        </code></pre>
