import csv
import json
from pathlib import Path
from pprint import PrettyPrinter
import requests
import sys
import toml


pp = PrettyPrinter(indent=4)
_verbose = False
def verbose(s):
    if _verbose:
        pp.pprint(s)


def fatal(s):
    print(s)
    exit(-1)


def not_found(s):
    fatal(f'not found: {s}')


# Helper class to keep a map between GitHub user name and login_id
class CanvasMapper:
    def __init__(self, cfg):
        self.mapping = {}
        self.cfg = cfg
        with open(cfg['map_path']) as f:
            reader = csv.DictReader(f.read().splitlines())
            for row in reader:
                self.mapping[row[cfg['github_col_name']]] = row[cfg['login_col_name']]
        verbose(self.mapping)

    def lookup(self, github_name):
        if github_name in self.mapping:
            return self.mapping[github_name]
        print('no mapping for ' + github_name)
        return ''


# Handles GET and PUT of scores to Canvas
class Canvas:
    def __init__(self, cfg, assignment_name, v=False):
        global _verbose
        _verbose = v
        self.scores = []
        self.assignment_name = assignment_name

        self.access_token = cfg['access_token']
        self.host_name = cfg['host_name']
        self.course_name = cfg['course_name']
    

    def make_auth_header(self):
        # The Authorization header is shared between GET and PUT
        return {
            'Authorization': 'Bearer {}'.format(self.access_token)
        }


    def make_url(self, path):
        # Combine the hostname and path, creating a requestable URL
        url = 'https://{}/{}'.format(self.host_name, path)
        verbose(url)
        return url


    # Use requests to GET the URL
    def get_url(self, url):
        # TODO: replace hard-coded access token with dynamic OAuth token
        headers = self.make_auth_header()
        response = requests.get(url, headers=headers)
        if response.status_code != requests.codes.ok:
            fatal('{} returned {}'.format(url, response.status_code))
        obj = json.loads(response.text)
        verbose(json.dumps(obj, indent=4, sort_keys=True))
        return obj


    # Create the URL for GET and PUT methods using Canvas IDs
    def make_submission_url(self, course_id, assignment_id, student_id):
        path = 'api/v1/courses/{}/assignments/{}/submissions/{}'.format(
            course_id,
            assignment_id,
            student_id
        )
        return self.make_url(path)
    

    # Download the grade for the specified course/assignment/student
    def get_submission(self, course_id, assignment_id, student_id):
        url = self.make_submission_url(course_id, assignment_id, student_id)
        obj = self.get_url(url)
        return obj['grade']


    # Upload the grade for the specified course/assignment/student
    def put_submission(self, course_id, assignment_id, student_id, score, comment):
        url = self.make_submission_url(course_id, assignment_id, student_id)
        headers = self.make_auth_header()
        data = {
            'submission[posted_grade]': score,
            'comment[text_comment]': comment
        }

        response = requests.put(url, data=data, headers=headers)
        if verbose and response.status_code != requests.codes.ok:
            d = json.loads(response.text)
            print(json.dumps(d, indent=4, sort_keys=True))

        return response.status_code == requests.codes.ok


    # Get the ID for the named course, e.g. "Computer Architecture - 01 (Spring 2022)"
    def get_course_id(self, course_name):
        course_id = None
        path = 'api/v1/courses'
        url = self.make_url(path)

        courses = self.get_url(url)
        for c in courses:
            if c['name'] == course_name:
                course_id = c['id']
                break

        if not course_id:
            not_found(course_name)
        verbose(f'course_id: {course_id}')
        return course_id


    # Get the ID for the named assignment, e.g. 'lab01'
    def get_assignment_id(self, course_id, assignment_name):
        assignment_id = None
        path = f'api/v1/courses/{course_id}/assignments'
        url = self.make_url(path)

        assignments = self.get_url(url)
        for a in assignments:
            if a['name'] == assignment_name:
                assignment_id = a['id']
                break

        if not assignment_id:
            not_found(assignment_name)
        verbose(f'assignment_id: {assignment_id}')
        return assignment_id


    # Download the list of students enrolled in the given course
    def get_enrollment(self, course_id):
        user_id = None
        # The enrollment API is paginated. 50 is "big enough" for our purposes
        path = f'api/v1/courses/{course_id}/enrollments?per_page=50'
        url = self.make_url(path)

        return self.get_url(url)


    # Add a Canvas user_id to each score dict so we can use the submission API
    def add_user_ids(self, scores, students):
        for score in scores:
            login_id = score['login_id']
            for student in students:
                if student['user']['login_id'] == login_id:
                    score['user_id'] = student['user_id']
                    break


    # Accumulate scores for later upload
    def add_score(self, login_id, score, comment):
        score = {
            'login_id': login_id,
            'score': score,
            'comment': comment
        }
        self.scores.append(score)


    # Upload the accumulated scores to Canvas
    def upload(self):
        course_id = self.get_course_id(self.course_name)
        assignment_id = self.get_assignment_id(course_id, self.assignment_name)
        students = self.get_enrollment(course_id)
        self.add_user_ids(self.scores, students)

        for s in self.scores:
            print('Uploading {} {}'.format(s['login_id'], s['score']), end=' ')
            if not 'user_id' in s:
                print('not enrolled')
                continue
            ok = self.put_submission(course_id, assignment_id, 
                s['user_id'], s['score'], s['comment'])
            print('ok' if ok else 'failed')


# Test harness
if __name__ == '__main__':
    # Comes from config file: course_name = sys.argv[1]
    assignment_name = sys.argv[1]
    login_id = sys.argv[2]
    score = sys.argv[3]
    comment = sys.argv[4]

    c = Canvas(assignment_name)
    c.add_score(login_id, score, comment)
    c.upload()
