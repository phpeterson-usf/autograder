from datetime import datetime
import os
import subprocess

from .cmd import cmd_exec_capture, cmd_exec_rc
from .util import *

class GitNoCommits(Exception):
    pass
class GitNoBranches(Exception):
    pass
class GitNoRepo(Exception):
    pass

class GitConfig(SafeConfig):
    def __init__(self, cfg):
        self.org = 'your GitHub Classroom org here'
        self.credentials = 'ssh'
        self.safe_update(cfg)


class Git:
    def __init__(self, git_cfg, args, date):
        self.cfg = GitConfig(git_cfg)
        self.args = args
        self.date = date


    def make_remote_path(self, repo):
        repo_path = repo.remote_path
        cred = self.cfg.credentials
        org = self.cfg.org
        if cred == 'ssh':
            return f'git@github.com:{org}/{repo_path}.git'
        elif cred == 'https':
            return f'https://github.com/{org}/{repo_path}'
        else:
            fatal(f'unknown Git.credentials: {cred}')


    def get_default_branch(self, local):
        branches = subprocess.Popen(
            ['git', 'remote', 'show', 'origin'],
            # ['git', 'branch', '--remotes', '--list', '*/HEAD'],
            stdout=subprocess.PIPE,
            cwd=local
        )
        cut = subprocess.Popen(
            ['sed', '-n',  '/HEAD branch/s/.*: //p'],
            # ['cut', '-d/', '-f3'],
            stdin=branches.stdout,
            stdout=subprocess.PIPE,
        )
        branch = cut.stdout.read().decode("utf-8").strip()
        if not branch:
            raise GitNoBranches
        return branch



    def get_commit_hash(self, local, branch):
        # append time if not provided in dates.toml
        time = '' if ' ' in self.date.date else ' 00:00:00'
        before = self.date.date + time
        cmd = ['git', 'rev-list', '-n', '1', '--first-parent', 
            "--pretty='%cd'", 'HEAD', '--date=local','--before', before, branch]
        lines =  cmd_exec_capture(cmd, wd=local)
        if len(lines) == 0:
            print(' '.join(cmd))
            raise GitNoCommits
        split_lines = lines.split("\n")
        commit_line = split_lines[0]
        date_line = split_lines[1]
        h = commit_line.split()[1][0:7]
        print(f'branch: {branch}, hash: {h}, date: {date_line}', end='')
        return h


    def clone(self, repo):
        remote = self.make_remote_path(repo)
        local = repo.local_path
        if os.path.isdir(local):
            print('Already exists: ' + local)
            return 0
        try:
            rc = cmd_exec_rc(['git', 'clone', remote, local])
            if rc != 0:
                raise GitNoRepo
            if self.args.by_date:
                branch = self.get_default_branch(local)
                commit_hash = self.get_commit_hash(local, branch)
                cmd_exec_rc(['git', 'checkout', commit_hash], wd=local)
        except GitNoRepo:
            print_red('No remote repo')
        except GitNoCommits:
            print_yellow('No commits in date range. Removing local repo')
            cmd_exec_rc(['rm', '-rf', local])
        except GitNoBranches:
            print_red('No branches in repo')
        print()


    def pull(self, repo):
        local = repo.local_path
        branch = self.get_default_branch(local)
        cmd_exec_rc(['git', 'checkout', branch], wd=local)
        cmd_exec_rc(['git', 'pull'], wd=local)


    def get_url_for_hash(self, comment, repo):
        local = repo.local_path
        remote = repo.remote_path
        try:
            cmd = ['git', 'rev-parse', '--short', 'HEAD']
            commit_hash = cmd_exec_capture(cmd, wd=local)
            url = f'https://github.com/{self.cfg.org}/{remote}/tree/{commit_hash}'
            return f'Test results for repo as of this commit: {url}\n\n' + comment
        except Exception as err:
            # Exceptions like FileNotFound were reported in test() 
            # Just leave any previous comment untouched
            return comment

    def get_newest_commit_date(self, repo):
        # TODO: it would be nice to make this work with a dev branch
        date_text = ''
        try:
            local = repo.local_path
            branch = self.get_default_branch(local)
            cmd = ['git', 'rev-list', '--first-parent', '--date=iso', '-n', '1', 
            '--pretty="%ai"', '--no-commit-header', branch, ]
            date_text = cmd_exec_capture(cmd, wd=local, capture_stderr=False)
            # remove double quotes which will cause fromisoformat() to fail
            date_text = date_text.replace('\"', '')
        except Exception as ex:
            print('get_newest_commit_date threw ', ex)
        return date_text
