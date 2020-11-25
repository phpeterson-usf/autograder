#!/usr/bin/env python3

import argparse
import os
import subprocess
import sys
import toml


def load_config(fname):
    # .toml file contains defaults. Command line args can override
    with open(fname) as f:
        defaults = toml.load(f)
    p = argparse.ArgumentParser()
    p.add_argument('action', type=str, choices=['clone', 'test'])
    p.add_argument('-c', '--credentials', choices=['https', 'ssh'], help='Github auth method',
        default=defaults.get('credentials', None))
    p.add_argument('-l', '--local', help='Local directory to test',
        default=defaults.get('local', None))
    p.add_argument('-o', '--org', help='Github Classroom Organization', 
        default=defaults.get('org', None))
    p.add_argument('-p', '--project', help='Project name', 
        default=defaults.get('project', None))
    p.add_argument('-s', '--students', nargs='+', type=str, help='Student Github IDs', 
        default=defaults.get('students', None))
    return vars(p.parse_args())


def load_tests(project):
    tests_fname = project + '.toml'
    tests_path = os.path.join('tests', tests_fname)
    with open(tests_path) as f:
        return toml.load(f)


def cmd_exec(args, wd=None):
    return subprocess.run(args, capture_output=True, timeout=2, cwd=wd)


def cmd_exec_rc(args):
    proc = cmd_exec(args)
    return proc.returncode


def cmd_exec_capture(args, wd=None, path=None):
    proc = cmd_exec(args, wd)
    if (path):
        # capture output written to path
        f = open(path, 'r')
        output = f.read()
        f.close()
    else:
        # capture output written to stdout
        output = proc.stdout.decode('utf-8')
    return output.rstrip('\n')


def print_green(s, e=''):
    print('\033[92m' + s + ' \033[0m', end=e)


def print_red(s, e=''):
    print('\033[91m' + s + ' \033[0m', end=e)


class Repo:
    def __init__(self, *args, **kwargs):
        # calculate the local and remote for this repo
        student = kwargs.get('student')
        if student:
            cfg = args[0]
            pg = cfg['project'] + '-' + student
            self.local = os.path.join('github.com', cfg['org'], pg)
            # set up remote repo for clone
            if cfg['credentials'] == 'https':
                self.remote = 'https://github.com/'
            elif cfg['credentials'] == 'ssh':
                self.remote = 'git@github.com:/'
            self.remote += cfg['org'] + '/' + pg + '.git'
        # allow -l/--local to override the local directory calculated above
        if kwargs.get('local'):
            self.local = kwargs['local'].rstrip('/')
        self.label = self.local.split('/')[-1]
        self.results = []


    def clone(self):
        if self.remote is None:
            raise Exception(self.label + ' no remote to clone')
        if os.path.isdir(self.local):
            return 0  # don't ask git to clone if local already exists
        return cmd_exec_rc(['git', 'clone', self.remote, self.local])


    def build(self):
        if not os.path.isdir(self.local):
            raise Exception(self.label + ' no repo to build')
        return cmd_exec_rc(['make', '-C', self.local])


    def test_one(self, executable, tests_dir, test):
        # build list of command line arguments, replacing the sentinel value $project_tests if it occurs
        args = [i.replace('$project_tests', tests_dir) for i in test['input']]
        args.insert(0, executable)

        # check to see if the test needs to be run in the repo dir
        run_in_repo = test.get('run_in_repo')
        wd = repo['path'] + '/' if run_in_repo else None

        if type(test['expected']) == list:
            # join them to match what we get from subprocess
            expected = '\n'.join(test['expected'])
        else: 
            expected = test['expected']

        score = 0
        try:
            output_file = test.get('output', 'stdout')
            if output_file == 'stdout':
                # get actual output from stdout
                actual = cmd_exec_capture(args, wd)
            else:
                # ignore stdout and get actual output from the specified file
                path = os.path.join(self.local, output_file)
                actual = cmd_exec_capture(args, wd, path)
            if actual.lower() == expected.lower():
                score = test['rubric']
        except subprocess.TimeoutExpired:
            raise Exception(self.label + ' timeout in test ' + test['name'])

        # record score for later printing
        result = {'test': test, 'score': score}
        self.results.append(result)


    def test(self, project, tests):
        executable = os.path.join(self.local, project)
        if not os.path.isfile(executable):
            raise Exception(self.label + ' no executable to test')
        tests_dir = os.path.join(os.getcwd(), 'tests', project)
        for test in tests['tests']:
            self.test_one(executable, tests_dir, test)


    def print_results(self, longest):
        print(self.label, end='')
        for n in range(longest - len(self.label)):
            print(' ', end='')

        earned = 0
        avail = 0
        for r in self.results:
            rubric = r['test']['rubric']
            avail += rubric
            if r['score'] == 0:
                print_red(r['test']['name'])
            else:
                earned += rubric
                print_green(r['test']['name'])

        print(f"{earned}/{avail}")


def main():
    cfg = load_config('config.toml')
    tests = load_tests(cfg['project'])
    if tests == {} or cfg == {}:
        return -1

    # Build list of repos to run, either from local or list of students
    repos = []
    if cfg.get('local'):
        # One local repo
        d = cfg['local']
        if not os.path.isdir(d):
            raise Exception(d + ' is not a directory')
        repo = Repo(cfg, local=d)
        repos.append(repo)
    elif cfg.get('students'):
        # Make repo list from student list
        for s in cfg['students']:
            repo = Repo(cfg, student=s)
            repos.append(repo)
    else:
        print('no local directory or students specified')
        return -1

    # Calc column width for justified printing
    longest = 0;
    for r in repos:
        l = len(r.label)
        if l > longest:
            longest = l
    longest += 1

    # Run all of the repos, either clone or test
    for repo in repos:
        try:
            if cfg['action'] == 'clone':
                repo.clone()
            elif cfg['action'] == 'test':
                repo.build()
                repo.test(cfg['project'], tests)
                repo.print_results(longest)
        except Exception as e:
            print_red(str(e), '\n')
            continue


if __name__ == "__main__":
    main()
