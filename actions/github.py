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


    def get_first_workflow_run(self, student):
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


    def get_run_log(self, student, run_id):
        # Download the logs for the most recent run
        url = self.make_log_url(student, run_id)
        log_zip = self.get_url(url, self.github_headers())

        # The logs for the workflow run are in zip format
        try:
            with ZipFile(BytesIO(log_zip)) as log_file:
                log_text = log_file.read('build/5_Test.txt').decode('utf-8')
        except Exception as e:
            log_text = 'Unzipping workflow log: ' + str(e)
            warn(log_text)

        return log_text


    def get_action_results(self, student):
        repo_result = init_repo_result(student)
        rubric = 100  # all or nothing?
        test_name = 'GitHub Workflow'
        tc_result = init_tc_result(rubric, test_name)
    
        # Ask github.com for the first action workflow
        run = self.get_first_workflow_run(student)
        if run:
            # Ask github.com for the log for that workflow run
            log_text = self.get_run_log(student, run['id'])
        else:
            log_text = 'No workflow runs found'
            warn(log_text)
        repo_result['comment'] = log_text

        # Mimic what Test.test() does for score accounting
        if run['conclusion'] == 'success':
            tc_result['score'] = repo_result['score'] = 100
            print_green(test_name)
        else:
            print_red(test_name)
        repo_result['results'].append(tc_result)
        return repo_result