#!/usr/bin/env python3

import json
import os
import subprocess
import sys


def json_load(path):
    try:
        with open(path) as json_file:
            return json.load(json_file)
    except FileNotFoundError:
        print('FileNotFound: ' + path)
        return {}


def tests_load(cfg):
    tests_fname = cfg['project'] + '.json'
    tests_path = os.path.join('tests', tests_fname)
    return json_load(tests_path)


def cmd_exec(args, wd=None):
    return subprocess.run(args, capture_output = True, timeout = 5, cwd=wd)


def cmd_exec_rc(args):
    proc = cmd_exec(args)
    return proc.returncode


def cmd_exec_stdout(args, wd=None):
    proc = cmd_exec(args, wd)
    return proc.stdout.decode('utf-8').rstrip('\n')


def repo_path(cfg, student):
    student_dir = cfg['project'] + '-' + student['github']
    return os.path.join('github.com', cfg['org'], student_dir)


def repo_clone(repo, cfg, student):
    if os.path.isdir(repo):
        return 0;
    remote = 'https://github.com/' + cfg['org'] + '/' + cfg['project'] + '-' + student['github']
    return cmd_exec_rc(['git', 'clone', remote, repo])


def repo_build(repo):
    return cmd_exec_rc(['make', '-C', repo])


def print_green(s):
    print('\033[92m' + s + ' \033[0m', end = '')


def print_red(s):
    print('\033[91m' + s + ' \033[0m', end = '')


def test_one(repo, executable, test):
    # build list of command line arguments
    args = [i for i in test['input']]
    args.insert(0, executable)

    # check to see if the test needs to be run in the repo dir
    run_in_repo = test.get('run_in_repo')
    wd = repo + '/' if run_in_repo else None

    if type(test['expected']) == list:
        # join them to match what we get from subprocess
        expected = '\n'.join(test['expected'])
    else: 
        expected = test['expected']

    if cmd_exec_stdout(args, wd).lower() == expected.lower():
        print_green(test['name'])
        score = test['rubric']
    else:
        print_red(test['name'])
        score = 0
    return score


def repo_test(repo, cfg, tests):
    score = 0;
    executable = repo + '/' + cfg['project']
    
    for test in tests['tests']:
        score += test_one(repo, executable, test)
    return score


def repo_build_test(repo, cfg, tests):
    if repo_build(repo) != 0:
        print('build failed')
        return False, 0
    else:
        return True, repo_test(repo, cfg, tests)


def main(argv):
    cfg = json_load('config.json')
    students = json_load('students.json')
    tests = tests_load(cfg)
    if tests == {} or cfg == {}:
        return -1

    # One local repo: build and test without cloning
    if len(argv) == 2:
        repo = argv[1]
        if not os.path.isdir(repo):
            print(repo + ' is not a directory')
            return -1
        print(repo + ' ', end = '')
        ok, score = repo_build_test(repo, cfg, tests)
        if ok == True:
            print(score)
        return 0

    # Calc column width for justified printing
    longest_github = 0;
    for student in students['students']:
        l = len(student['github'])
        if l > longest_github:
            longest_github = l
    longest_github += 1

    for student in students['students']:

        # Justify columns by width of github ID
        print(student['github'], end = '')
        for i in range (longest_github - len(student['github'])):
            print(' ', end = '')

        # Clone
        repo = repo_path(cfg, student)
        if repo_clone(repo, cfg, student) != 0:
            print('clone failed')
            continue

        # Build and test
        ok, score = repo_build_test(repo, cfg, tests)
        if ok == False:
            continue
        print(score)


if __name__ == "__main__":
    main(sys.argv)
