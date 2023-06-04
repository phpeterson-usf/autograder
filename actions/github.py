"""
github.py uses the GitHub REST API to get the result of a GitHub action workflow
"""

from io import BytesIO
from zipfile import ZipFile

from actions.git import *
from actions.server import Server

from actions.util import *

class GithubConfig(Config):
    def __init__(self, cfg):
        self.host_name = 'api.github.com'
        self.access_token = None
        self.safe_update(cfg)

 
class Github(Server):
    def __init__(self, cfg, args, org):
        self.github_cfg = GithubConfig(cfg)
        super().__init__(
            self.github_cfg.host_name, 
            self.github_cfg.access_token, 
            args.verbose)
        self.project = args.project
        self.org = org


    def github_headers(self):
        return {
            'Accept': 'application/vnd.github+json',
            'X-GitHub-Api-Version': '2022-11-28'
        }
    

    def make_action_runs_url(self, student):
        url = 'https://{}/repos/{}/{}-{}/actions/runs'.format(
                self.github_cfg.host_name, self.org, self.project, student)
        return url


    def make_log_url(self, student, run_id):
        url = self.make_action_runs_url(student)
        url += f'/{run_id}/logs'
        return url


    def get_first_action_run(self, student):
        # Get all of the workflow runs
        url = self.make_action_runs_url(student)
        runs = self.get_url(url, self.github_headers())

        run = {}
        try:
            # The first run in the workflow_runs list is the most recent
            run = runs['workflow_runs'][0]
        except Exception as e:
            warn('Accessing first workflow run: ' + str(e))
        return run


    def get_action_run_summary_url(self, student, run):
        run_url = self.make_action_runs_url(student)
        jobs_url = run_url + f'/{run["id"]}/jobs'
        jobs = self.get_url(jobs_url, self.github_headers())
        if jobs:
            job_id = jobs['jobs'][0]['id']
            return 'https://github.com/{}/{}-{}/actions/runs/{}#summary-{}'.format(
                self.org, self.project, student, run['id'], job_id)
        else:
            w = f'No jobs found for {student} run_id: {run["id"]}'
            warn(w)
            return w


    def get_action_run_score(self, student, run):
        score = None
        # Download the logs for the most recent run
        url = self.make_log_url(student, run['id'])
        log_zip = self.get_url(url, self.github_headers())

        # The logs for the workflow run are in zip format
        try:
            with ZipFile(BytesIO(log_zip)) as log_file:
                log_text = log_file.read('1_Autograder Results.txt').decode('utf-8')
            for line in log_text.split('\n'):
                # Split off the timestamp part of the line
                line_parts = line.split(' ', 1)
                if len(line_parts) > 1:
                    second_part = line_parts[1]
                    score_parts = second_part.split('=', 1)
                    # Find the line which specifies the score
                    if score_parts[0] == 'FINAL_SCORE':
                        # Split off the earned points from the possible points
                        score = score_parts[1].split('/')[0]
        except Exception as e:
            log_text = 'Analyzing action log: ' + str(e)
            warn(log_text)

        if score == None:
            warn('No score found in action log')
        return score


    def get_action_results(self, student):
        repo_result = init_repo_result(student)
    
        # Ask github.com for the first action run
        run = self.get_first_action_run(student)
        if run:
            # Ask github.com for the log for that workflow run
            repo_result['score'] = self.get_action_run_score(student, run)
            # Calculate the web browser (not "api) URL for the first job ID in the action run
            repo_result['comment'] = self.get_action_run_summary_url(student, run)
        else:
            log_text = 'No workflow runs found'
            warn(log_text)

        # Notice no test case results are generated here. The idea is that
        # students go to the "action/run/job/JJJ" URL on github.com to see 
        # the detailed testing results
        return repo_result