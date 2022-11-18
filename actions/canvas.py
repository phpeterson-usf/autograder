import csv
import json
from pathlib import Path
from pprint import PrettyPrinter
import requests
import sys

from actions.util import *

pp = PrettyPrinter(indent=4)
_verbose = False
def verbose(s):
    if _verbose:
        pp.pprint(s)


def not_found(s):
    fatal(f'not found: {s}')


# Helper class to keep a map between GitHub user name and Canvas login_id
class CanvasMapper:

    default_cfg = {
        'map_path': 'your CSV mapping file here',
        'github_col_name': 'GitHub',
        'login_col_name': 'SIS Login ID',
    }


    @staticmethod
    def from_cfg(mapper_cfg):
        return json.loads(json.dumps(mapper_cfg.__dict__), object_hook=CanvasMapper)


    def __init__(self, mapper_cfg):
        self.__dict__.update(mapper_cfg)
        self.mapping = {}

        abs_path = Path(self.map_path).expanduser()
        with open(abs_path) as f:
            failures = []
            reader = csv.DictReader(f.read().splitlines())
            for row in reader:
                github = row[self.github_col_name]
                login = row[self.login_col_name]
                if not github:
                    # accumulate students with empty GitHub username
                    failures.append(login) 

                # set up mapping from login ID to GitHub username
                self.mapping[github] = login
            if failures:
                # print out students with empty github username
                # so they can be fixed as a batch
                fatal(f'No github IDs for logins: {str(failures)}')
        verbose(self.mapping)


    def lookup(self, github_name):
        if github_name in self.mapping:
            return self.mapping[github_name]
        print('no mapping for ' + github_name)
        return ''


    def get_github_list(self):
        github_list = []
        for github in self.mapping:
            github_list.append(github)
        return github_list


# Handles GET and PUT of scores to Canvas
class Canvas:

    default_cfg = {
        'host_name': 'usfca.test.instructure.com or canvas.instructure.com',
        'access_token': 'your access token here',
        'course_name': 'e.g. Computer Architecture - 01 (Spring 2022)',
    }

    @staticmethod
    def from_cfg(canvas_cfg, args):
        canvas = json.loads(json.dumps(canvas_cfg.__dict__), object_hook=Canvas)
        canvas.args = args
        global _verbose
        _verbose = args.verbose
        return canvas


    def __init__(self, canvas_cfg):
        self.__dict__.update(canvas_cfg)
        self.scores = []
        self.args = None
    

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
        path = f'api/v1/courses/{course_id}/assignments?per_page=50'
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
        assignment_id = self.get_assignment_id(course_id, self.args.project)
        students = self.get_enrollment(course_id)
        self.add_user_ids(self.scores, students)

        for s in self.scores:
            print('Uploading {} {}'.format(s['login_id'], s['score']), end=' ')
            if not 'user_id' in s:
                print_red('not enrolled', e='\n')
                continue
            ok = self.put_submission(course_id, assignment_id, 
                s['user_id'], s['score'], s['comment'])
            if ok:
                print_green('ok', e='\n')
            else:
                print_red('failed', e='\n')

"""
# Test harness
if __name__ == '__main__':
    # Comes from config file: course_name = sys.argv[1]
    assignment_name = sys.argv[1]
    login_id = sys.argv[2]
    score = sys.argv[3]
    comment = sys.argv[4]

    c = Canvas.from_cfg(cfg)
    c.add_score(login_id, score, comment)
    c.upload()
"""
