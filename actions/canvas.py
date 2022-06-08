import json
from pathlib import Path
import requests
import sys
import toml

verbose = False

# Create the URL for GET and PUT methods, substituting Canvas IDs for human-readable names
# http://staff.createthenext.com/doc/api/submissions.html#method.submissions_api.update
def canvas_url(config, argv):
    # 
    course_name = argv[2]
    course = config[course_name]
    assignment_name = argv[3]
    student_name = argv[4]
    student_id = config['students'][student_name]

    path = 'api/v1/courses/{}/assignments/{}/submissions/{}'.format(
        course['id'],
        course[assignment_name]['id'],
        student_id
    )
    url = 'https://{}/{}?access_token={}'.format(
        config['host_name'], 
        path,
        config['access_token']
    )
    if verbose:
        print(url)
    return url


# Download the grade for the specified course/assignment/student
def canvas_get(url):
    response = requests.get(url)
    if response.status_code == requests.codes.ok:
        d = json.loads(response.text)
        if verbose:
            print(json.dumps(d, indent=4, sort_keys=True))
        return d['grade']


# Upload the new score for the specified course/assignment/student
# https://community.canvaslms.com/t5/Canvas-Developers-Group/Add-grade-using-canvas-submission-API/td-p/60436
def canvas_put(url, score):
    
    data = {'submission[posted_grade]': score}
    response = requests.put(url, data=data)
    if verbose and response.status_code != requests.codes.ok:
        d = json.loads(response.text)
        print(json.dumps(d, indent=4, sort_keys=True))
    return response.status_code


# Test harness

if __name__ == '__main__':

    method = sys.argv[1]

    toml_path = Path.home() / '.config' / 'canvas' / 'config.toml'
    with open(toml_path) as f:
        config = toml.loads(f.read())
        if verbose:
            print(config)

    url = canvas_url(config, sys.argv)

    if method == 'get':
        grade = canvas_get(url)
        print(grade)
    elif method == 'put':
        score = sys.argv[5]
        status_code = canvas_put(url, score)
        print(status_code)
