# autograder
1. Clone and build repos from Github Classroom. 
2. Run test cases vs. expected output
3. Generate a score based on a rubric for each test case

## Requirements
1. Requires python3
1. For JSON, remember that there's no comma on the last object. If you include a 
comma after the last object, you'll get a syntax error parsing the JSON file.

## Usage for students
You will need a file called config.json which contains the Github Classroom organization
name and the project name for each project you work on. Example
<pre><code>
pi@raspberrypi:~/phpeterson-usf/autograder $ cat config.json
{
    "org": "cs-315-03-20f",
    "project": "project02"
}
</code></pre>
<pre><code>
$ git clone https://github.com/phpeterson-usf/autograder.git
$ cd autograder
$ python3 autograder.py ~/project02
/home/pi/project02 01 02 03 04 05 06 07 08 09 10 11 12 13 14 15 16 17 18 19 20 100
</code></pre>

## Usage for instructors
1. Test cases for each project are expressed in JSON, as you can see in the `tests/` directory
1. Test case inputs are a list of strings for each command-line flag and value, since
that's how python subprocess takes arguments. Maybe there's a better way
    <pre><code>pi@raspberrypi:~/phpeterson-usf/autograder/tests $ cat project02.json
    {
        "tests": [
            {
                "name": "01",
                "input": ["-e", "1 + 1"],
                "expected": "2",
                "rubric": 5
            },
            {
                "name": "02",
                "input": ["-e", "10", "-b", "16"],
                "expected": "0x0000000A",
                "rubric": 5
            }
        ]
    }</code></pre>
1. You can make up a JSON file with your list of students, and autograder will loop
over the list, cloning, building, and testing each one. Each student object contains:
    1. A property called "github" for the student's Github ID
    2. A property called "login" for mapping the student's Github ID to a Canvas ID, 
    as used at usfca.edu where I teach
        <pre><code>pi@raspberrypi:~/phpeterson-usf/autograder $ cat students.json
        {
            "students": [
                {
                    "github": "phpeterson-usf",
                    "login": "test"
                },
                {
                    "github": "gdbenson",
                    "login": "test"
                }
            ]
        }</code></pre>
