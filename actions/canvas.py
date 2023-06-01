import csv
from pathlib import Path

from actions.util import *
from actions.server import Server

class CanvasMapperConfig(Config):
    def __init__(self, cfg):
        self.map_path = 'your CSV mapping file here'
        self.github_col_name = 'GitHub'
        self.login_col_name = 'SIS Login ID'
        self.safe_update(cfg)


# Helper class to keep a map between GitHub user name and Canvas login_id
class CanvasMapper:

    def __init__(self, map_cfg):
        self.map_cfg = CanvasMapperConfig(map_cfg)
        self.mapping = {}

        abs_path = Path(self.map_cfg.map_path).expanduser()
        with open(abs_path) as f:
            failures = []
            gh_col_name = self.map_cfg.github_col_name
            login_col_name = self.map_cfg.login_col_name
            reader = csv.DictReader(f.read().splitlines())
            for row in reader:
                github = row[gh_col_name]
                login = row[login_col_name]
                if not github:
                    # accumulate students with empty GitHub username
                    failures.append(login) 

                # set up mapping from login ID to GitHub username
                self.mapping[github] = login
            if failures:
                # print out students with empty github username
                # so they can be fixed as a batch
                fatal(f'No github IDs for logins: {str(failures)}')


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


class CanvasConfig(Config):
    def __init__(self, cfg):
        self.host_name = 'usfca.test.instructure.com or canvas.instructure.com'
        self.access_token = 'your access token here'
        self.course_name = 'e.g. Computer Architecture - 01 (Spring 2022)'
        self.safe_update(cfg)


# Handles GET and PUT of scores to Canvas
class Canvas(Server):

    def __init__(self, canvas_cfg, args):
        self.canvas_cfg = CanvasConfig(canvas_cfg)
        super().__init__(self.canvas_cfg.host_name, self.canvas_cfg.access_token, args.verbose)
        self.scores = []
        self.args = args
    

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
        data = {
            'submission[posted_grade]': score,
            'comment[text_comment]': comment
        }
        return self.put_url(url, {}, data)


    # Get the ID for the named course, e.g. "Computer Architecture - 01 (Spring 2022)"
    def get_course_id(self, course_name):
        course_id = None
        path = 'api/v1/courses?per_page=100'
        url = self.make_url(path)

        courses = self.get_url(url)
        for c in courses:
            if not 'name' in c:
                continue

            if c['name'] == course_name:
                course_id = c['id']
                break

        if not course_id:
            self.not_found(course_name)
        self.verbose(f'course_id: {course_id}')
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
            self.not_found(assignment_name)
        self.verbose(f'assignment_id: {assignment_id}')
        return assignment_id


    # Download the list of students enrolled in the given course
    def get_enrollment(self, course_id):
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
        course_id = self.get_course_id(self.canvas_cfg.course_name)
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
