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
        self.access_token = 'your access token here'
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

    def make_repo_artifacts_url(self, student):
        url = 'https://{}/repos/{}/{}-{}/actions/artifacts'.format(
                self.github_cfg.host_name, self.org, self.project, student)
        return url


    def get_first_artifact_for_repo(self, student):
        # Get all artifacts for the workflow run
        url = self.make_repo_artifacts_url(student)

        artifact = {}
        try:
            artifacts = self.get_url(url, self.github_headers())
            # The first artifact in the artifacts list is the most recent
            artifact = artifacts['artifacts'][0]
        except Exception as e:
            warn('Accessing first artifact: ' + str(e))
        return artifact

    def get_action_run_summary_url(self, student, artifact):
        run_url = self.make_action_runs_url(student)
        run_id = artifact['workflow_run']['id']
        jobs_url = run_url + f'/{run_id}/jobs'
        jobs = self.get_url(jobs_url, self.github_headers())
        if jobs:
            job_id = jobs['jobs'][0]['id']
            return 'https://github.com/{}/{}-{}/actions/runs/{}#summary-{}'.format(
                self.org, self.project, student, run_id, job_id)
        else:
            w = f'No jobs found for {student} run_id: {run_id}'
            warn(w)
            return w


    def get_artifact_results(self, artifact):
        results = None
        # Download the artifact
        url = artifact['archive_download_url']
        artifact_zip = self.get_url(url, self.github_headers())

        # The logs for the workflow run are in zip format
        try:
            with ZipFile(BytesIO(artifact_zip)) as log_file:
                results = log_file.read('grade-results.json')
                results = json.loads(results.decode('utf-8'))
                results['grade'] = float(results['grade'])
        except Exception as e:
            log_text = 'Analyzing artifact: ' + str(e)
            warn(log_text)

        if results == None:
            warn('No results found in artifact')
        return results

    def get_action_results(self, student):
        repo_result = init_repo_result(student)
    
        # Ask github.com for the first artifact run
        artifact = self.get_first_artifact_for_repo(student)
        if artifact:
            # Download the artifact and extract the grade
            results = self.get_artifact_results(artifact)
            repo_result['score'] = results['grade']
            # Calculate the web browser (not "api) URL for the first job ID in the action run
            repo_result['comment'] = self.get_action_run_summary_url(student, artifact)
        else:
            log_text = 'No artifacts found'
            repo_result['comment'] = log_text
            warn(log_text)

        # Notice no test case results are generated here. The idea is that
        # students go to the "action/run/job/JJJ" URL on github.com to see 
        # the detailed testing results
        return repo_result
