import json
import os
from actions.cmd import cmd_exec_capture, cmd_exec_rc
from actions.util import fatal, make_local_path


class Git:
    default_cfg = {
        'org': 'your GitHub Classroom org here',
        'credentials': 'ssh',
    }

    @staticmethod
    def from_cfg(git_cfg, args):
        git = json.loads(json.dumps(git_cfg.__dict__), object_hook=Git)
        git.args = args
        return git


    def __init__(self, git_cfg):
        self.__dict__.update(git_cfg)
        self.args = None


    def make_local(self, student):
        return make_local_path(self.args.project, student)


    def make_remote(self, student):
        if self.credentials == 'ssh':
            return f'git@github.com:/{self.org}/{self.args.project}-{student}'
        elif self.credentials == 'https':
            return f'https://github.com/{self.org}/{self.args.project}-{student}'
        else:
            fatal('unknown Git.credentials: ' + self.credentials)


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
        return branch


    def get_commit_hash(self, local, branch):
        # append time if not provided on the command line
        time = '' if ' ' in self.args.date else ' 00:00:00'
        deadline = '\'' + self.args.date + time + '\''
        cmd = ['git', 'rev-list', '-n', '1', '--first-parent', 
            "--pretty='%cd'", 'HEAD', '--date=local','--before', deadline, branch]
        lines =  cmd_exec_capture(cmd, wd=local)
        if len(lines) == 0:
            print(f'no commits before {deadline}', end='')
            return None
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
        rc = cmd_exec_rc(['git', 'clone', remote, local])
        if rc != 0:
            print('No repo: ' + remote)
            return 0
        if self.args.date:
            branch = self.get_default_branch(local)
            commit_hash = self.get_commit_hash(local, branch)
            if commit_hash:
                cmd_exec_rc(['git', 'checkout', commit_hash], wd=local)
        print()


    def pull(self, student):
        local = self.make_local(student)
        branch = self.get_default_branch(local)
        cmd_exec_rc(['git', 'checkout', branch], wd=local)
        cmd_exec_rc(['git', 'pull'], wd=local)
