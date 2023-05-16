import json
import os
from actions.cmd import cmd_exec_capture, cmd_exec_rc
from actions.util import fatal, make_repo_path, print_red
import subprocess

class GitNoCommits(Exception):
    pass
class GitNoBranches(Exception):
    pass
class GitNoRepo(Exception):
    pass

class Git:
    default_cfg = {
        'org': 'your GitHub Classroom org here',
        'credentials': 'ssh',
    }

    def __init__(self, git_cfg, args):
        self.cfg = git_cfg
        self.args = args


    def make_local(self, student):
        return make_repo_path(self.args.project, student)


    def make_remote(self, student):
        repo_path = make_repo_path(self.args.project, student)
        cred = self.cfg['credentials']
        org = self.cfg['org']
        if cred == 'ssh':
            return f'git@github.com:{org}/{repo_path}.git'
        elif cred == 'https':
            return f'https://github.com/{org}/{repo_path}'
        else:
            fatal(f'unknown Git.credentials: {cred}')


    def get_default_branch(self, local):
        branches = subprocess.Popen(
            ['git', 'branch', '--remotes', '--list', '*/HEAD'],
            stdout=subprocess.PIPE,
            cwd=local
        )
        cut = subprocess.Popen(
            ['cut', '-d/', '-f3'],
            stdin=branches.stdout,
            stdout=subprocess.PIPE,
        )
        branch = cut.stdout.read().decode("utf-8").strip()
        if not branch:
            raise GitNoBranches
        return branch
        


    def get_commit_hash(self, local, branch):
        # append time if not provided on the command line
        time = '' if ' ' in self.args.date else ' 00:00:00'
        deadline = '\'' + self.args.date + time + '\''
        cmd = ['git', 'rev-list', '-n', '1', '--first-parent', 
            "--pretty='%cd'", 'HEAD', '--date=local','--before', deadline, branch]
        lines =  cmd_exec_capture(cmd, wd=local)
        if len(lines) == 0:
            raise GitNoCommits
        split_lines = lines.split("\n")
        commit_line = split_lines[0]
        date_line = split_lines[1]
        h = commit_line.split()[1][0:7]
        print(f'branch: {branch}, hash: {h}, date: {date_line}', end='')
        return h


    def clone(self, student):
        remote = self.make_remote(student)
        local = self.make_local(student)
        if os.path.isdir(local):
            print('Already exists: ' + local)
            return 0
        try:
            rc = cmd_exec_rc(['git', 'clone', remote, local])
            if rc != 0:
                raise GitNoRepo
            if self.args.date:
                branch = self.get_default_branch(local)
                commit_hash = self.get_commit_hash(local, branch)
                cmd_exec_rc(['git', 'checkout', commit_hash], wd=local)
        except GitNoRepo:
            print_red('No remote repo')
        except GitNoCommits:
            print_red('No commits before deadline. Removing local repo')
            cmd_exec_rc(['rm', '-rf', local])
        except GitNoBranches:
            print_red('No branches in repo')
        print()


    def pull(self, student):
        local = self.make_local(student)
        branch = self.get_default_branch(local)
        cmd_exec_rc(['git', 'checkout', branch], wd=local)
        cmd_exec_rc(['git', 'pull'], wd=local)
