import json
from pathlib import Path
import requests
import sys
import toml

verbose = False


def fatal(s):
    print(s)
    exit(-1)


def not_found(s):
    fatal('not found: {}'.format(s))


def canvas_config():
    # Load IDs for courses, assignments, and students from config file
    toml_path = Path.home() / '.config' / 'canvas' / 'config.toml'
    with open(toml_path) as f:
        config = toml.loads(f.read())
        if verbose:
            print(config)
    return config


# The Authorization header is shared between GET and PUT
def auth_header(config):
    return {'Authorization': 'Bearer {}'.format(config['access_token'])}


# Add the hostname and access token to a path, creating a requestable URL
def canvas_url(config, path):
    url = 'https://{}/{}'.format(config['host_name'], path)
    if verbose:
        print(url)
    return url


# Use requests to GET the URL
def canvas_url_get(config, url):
    # TODO: replace hard-coded access token with dynamic OAuth token
    headers = auth_header(config)
    response = requests.get(url, headers=headers)
    if response.status_code != requests.codes.ok:
        fatal('{} returned {}'.format(url, response.status_code))
    obj = json.loads(response.text)
    if verbose:
        print(json.dumps(obj, indent=4, sort_keys=True))
    return obj


# Create the URL for GET and PUT methods using Canvas IDs
# http://staff.createthenext.com/doc/api/submissions.html#method.submissions_api.update
def canvas_submission_url(config, course_id, assignment_id, student_id):
    path = 'api/v1/courses/{}/assignments/{}/submissions/{}'.format(
        course_id,
        assignment_id,
        student_id
    )
    return canvas_url(config, path)
    

# Download the grade for the specified course/assignment/student
def canvas_submission_get(config, course_id, assignment_id, student_id):
    url = canvas_submission_url(config, course_id, assignment_id, student_id)
    d = canvas_url_get(config, url)
    return d['grade']


# Upload the new score for the specified course/assignment/student
# https://community.canvaslms.com/t5/Canvas-Developers-Group/Add-grade-using-canvas-submission-API/td-p/60436
def canvas_submission_put(config, course_id, assignment_id, student_id, score):
    url = canvas_submission_url(config, course_id, assignment_id, student_id)
    data = {'submission[posted_grade]': score}
    headers = auth_header(config)

    response = requests.put(url, data=data, headers=headers)
    if verbose and response.status_code != requests.codes.ok:
        d = json.loads(response.text)
        print(json.dumps(d, indent=4, sort_keys=True))

    return response.status_code == requests.codes.ok


# Get the ID for the named course
# Course name in Canvas must match the given name
# I tried to use enrollment term but only root_users have those :-(
def canvas_course_get(config, course_name):
    course_id = None
    path = 'api/v1/courses'
    url = canvas_url(config, path)

    courses = canvas_url_get(config, url)
    for c in courses:
        if c['name'] == course_name:
            course_id = c['id']
            break

    if not course_id:
        not_found(course_name)
    if verbose:
        print('course_id: ', course_id)
    return course_id


# Given a course, get the ID for the named assignment
# Assignment name in Canvas must match the given name
def canvas_assignment_get(config, course_id, assignment_name):
    assignment_id = None
    path = f'api/v1/courses/{course_id}/assignments'
    url = canvas_url(config, path)

    assignments = canvas_url_get(config, url)
    for a in assignments:
        if a['name'] == assignment_name:
            assignment_id = a['id']

    if not assignment_id:
        not_found(assignment_name)
    if verbose:
        print('assignment_id: ', assignment_id)
    return assignment_id


# Given a course, get the ID for the named student
# SIS Login ID in Canvas must match the given name
def canvas_enrollment_get(config, course_id, student_name):
    user_id = None
    path = f'api/v1/courses/{course_id}/enrollments'
    url = canvas_url(config, path)

    students = canvas_url_get(config, url)
    for s in students:
        if s['user']['login_id'] == student_name:
            user_id = s['user_id']

    if not user_id:
        not_found(student_name)
    if verbose:
        print('user_id: ', user_id)
    return user_id

 
# Test harness
if __name__ == '__main__':
    config = canvas_config()

    # In autograder I'll get each ID once for better performance
    method = sys.argv[1]
    course_id = canvas_course_get(config, sys.argv[2])
    assignment_id = canvas_assignment_get(config, course_id, sys.argv[3])
    student_id = canvas_enrollment_get(config, course_id, sys.argv[4])

    if method == 'get':
        grade = canvas_submission_get(config, course_id, assignment_id, student_id)
        print(grade)
    elif method == 'put':
        score = sys.argv[5]
        ok = canvas_submission_put(config, course_id, assignment_id, student_id, score)
        if ok:
            print('ok')
        else:
            print('failed: {}', status_code)
