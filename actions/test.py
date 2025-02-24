from datetime import datetime as dt
import difflib
import json
import os
from subprocess import CalledProcessError, TimeoutExpired
import traceback

from actions.cmd import cmd_exec_capture, cmd_exec_rc, TIMEOUT
from actions.util import *
from actions.github import *

# One test case out of the list in the TOML test case file

class TestCaseConfig(Config):
    def __init__(self, cfg):
        self.case_sensitive = False
        self.expected = None
        self.input = None
        self.name = None
        self.output = 'stdout'
        self.rubric = 0
        self.safe_update(cfg)


class TestCase:
    def __init__(self, tc_cfg, project_cfg, args):
        self.tc_cfg = TestCaseConfig(tc_cfg)
        self.args = args  # need verbose, project
        self.project_cfg = project_cfg  # need strip_output and TIMEOUT
        self.cmd_line = []
        #self.validate()


    def validate(self):
        test_name = self.tc_cfg.name
        if type(self.tc_cfg.rubric) is not int:
            print(f'Rubric for test \"{test_name}\" must be an integer')
        if type(self.tc_cfg.input) is not list:
            print(type(self.tc_cfg.input))
            #TODO fatal(f'Input for test \"{test_name}\" must be a list')
        if type(self.tc_cfg.expected) is not str:
            print(type(self.tc_cfg.expected))
            fatal(f'Expected output for test \"{test_name}\" must be a string')


    def init_cmd_line(self, digital_path, project_tests_path):
        for i in self.tc_cfg.input:
            if '$project_tests' in i:
                param = i.replace('$project_tests', project_tests_path)
            elif '$project' in i:
                param = i.replace('$project', self.args.project)
            elif '$digital' in i:
                param = i.replace('$digital', digital_path)
            elif '$name' in i:
                param = i.replace('$name', self.tc_cfg.name)
            else:
                param = i
            self.cmd_line.append(param)


    def init_expected(self, project_tests_path):
        # the expected output can refer to $project_tests by pathname
        self.tc_cfg.expected = self.tc_cfg.expected.replace('$project_tests', project_tests_path)


    def get_actual_go(self, jlines):
        act = ''
        for jline in jlines.split('\n'):
            d = json.loads(jline)
            a = d.get('Action')
            # if we encounter "Action":"pass" declare victory
            if a and a == 'pass':
                return a
            # collect "Output" values so we have them for the failure case
            # use one string to mimic what we would get from stdout
            o = d.get('Output')
            if o:
                if 'warning: no tests to run' in o:
                    # this is unfortunate. "no tests to run" generates a "pass"
                    return o
                act += o
        return act


    def get_actual(self, local):
        timeout = self.project_cfg.timeout
        capture_stderr = self.project_cfg.capture_stderr
        if self.tc_cfg.output == 'stdout':
            # get actual output from stdout
            act = cmd_exec_capture(self.cmd_line, local, timeout=timeout, 
                                   capture_stderr=capture_stderr)
        else:
            # ignore stdout and get actual output from the specified file
            path = os.path.join(local, self.tc_cfg.output)
            act = cmd_exec_capture(self.cmd_line, local, path, timeout=timeout,
                                   capture_stderr=capture_stderr)
    
        if self.project_cfg.strip_output:
            act = act.replace(self.project_cfg.strip_output, '')
        if self.project_cfg.build == 'go':
            act = self.get_actual_go(act)
        return act

    def prepare_cmd_line(self, cmd_line):
        cmd_line_prepared = [cmd_line[0]]
        for arg in cmd_line[1:]:
            if ' ' in arg:
                arg = '"' + arg + '"'
            cmd_line_prepared.append(arg)
        return cmd_line_prepared

    def make_lines(self, text):
        text_lines = []
        if not self.tc_cfg.case_sensitive:
            text = text.lower()
        for line in text.split('\n'):
            text_lines.append(line.strip() + '\n')
        return text_lines
        
    def match_expected(self, actual):
        # rstrip to remove extra trailing newline
        exp = self.make_lines(self.tc_cfg.expected.rstrip())
        act = self.make_lines(actual.rstrip())

        cmd_line = self.prepare_cmd_line(self.cmd_line)
        cmd_line_str = ' '.join(cmd_line)

        if self.args.very_verbose:
            print(f"\n\n===[{self.tc_cfg.name}]===expected\n$ {cmd_line_str}\n{exp}")
            print()
            print(f"===[{self.tc_cfg.name}]===actual\n$ {cmd_line_str}\n{act}")

        if self.args.verbose and (act != exp):
            print(f"\n\n===[{self.tc_cfg.name}]===diff\n$ {cmd_line_str}")
            diff = difflib.context_diff(exp, act, fromfile='expected', tofile='actual')
            for line in diff:
                print(line, end='')

        return act == exp


class TestConfig(Config):
    def __init__(self, cfg):
        self.tests_path = '~/tests'
        self.digital_path = '~/Digital/Digital.jar' # TODO how does this connect with [Digital]?
        self.safe_update(cfg)


class ProjectConfig(Config):
    def __init__(self, cfg):
        self.build = 'make'
        self.strip_output = None
        self.subdir = None
        self.timeout = TIMEOUT
        self.capture_stderr = True
        self.due_date = None
        self.late_penalty = 0.03
        self.safe_update(cfg)

class Test:

    def __init__(self, test_cfg, args):
        self.test_cfg = TestConfig(test_cfg)    
        self.args = args
        self.tests_path = os.path.expanduser(self.test_cfg.tests_path)
        self.digital_path = os.path.expanduser(self.test_cfg.digital_path)
        self.test_cases = []
        self.load_test_cases()
        self.build_err = ''

    def load_test_cases(self):
        # Load <project>.toml
        path = os.path.join(
            self.tests_path,
            self.args.project,
            self.args.project + '.toml'
        )
        toml_doc = load_toml(path)
        if not toml_doc:
            warn(f'File not found: {path}. Suggest "git pull" in tests repo')

        # Load the [project] table which contains project-specific config
        self.project_cfg = ProjectConfig(toml_doc.get('project', {}))

        # Create test cases for each element of the [tests] table
        project_tests_path = os.path.join(self.tests_path, self.args.project)
        tests = toml_doc.get('tests', {})
        if not tests:
            warn(f'No test cases found: {path}')
        for tc_cfg in tests:
            tc = TestCase(tc_cfg, self.project_cfg, self.args)
            tc.init_expected(project_tests_path)
            tc.init_cmd_line(self.digital_path, project_tests_path)
            self.test_cases.append(tc)


    def build(self, repo_path):
        build_err = None
        b = self.project_cfg.build
        if b == 'none':
            return
        if b == 'make':
            if not os.path.exists(repo_path):
                build_err = f'Repo not found: {repo_path}'
            else:
                mfu_path = os.path.join(repo_path, 'Makefile')
                mfl_path = os.path.join(repo_path, 'makefile')
                if not os.path.isfile(mfu_path) and not os.path.isfile(mfl_path):
                    build_err = f'Makefile not found: {mfu_path}'
                else:
                    if cmd_exec_rc(['make', '-C', repo_path], timeout=30) != 0:
                        build_err = 'Program did not make successfully'
        elif b == 'go':
            if cmd_exec_rc(['go', 'build']) != 0:
                build_error = 'go build failed'
        else:
            fatal(f'Unknown build plan: \"{b}\"')

        if build_err and self.args.verbose:
            print_red(build_err, '')
        return build_err

    def run_one_test(self, repo_path, test_case):
        '''
        Manage exceptions here so we can
        1. print them out in a friendly way
        2. record the failed test case
        3. keep going to the next test cases and repos
        '''
        result = init_tc_result(test_case.tc_cfg.rubric, test_case.tc_cfg.name)
        actual = ''
        friendly_str = ''
        tb_str = ''
        try:
            actual = test_case.get_actual(repo_path)
            if test_case.match_expected(actual):
                # Test case passed, accumulate score
                result['score'] = test_case.tc_cfg.rubric
        except CalledProcessError:
            friendly_str = 'Program crashed'
            tb_str = traceback.format_exc()
        except TimeoutExpired:
            friendly_str = 'Program timed out (infinite loop?)'
            tb_str = traceback.format_exc()
        except PermissionError:
            friendly_str = 'Program is not executable'
            tb_str = traceback.format_exc()
        except FileNotFoundError:
            friendly_str = 'Program not found (build failed?)'
            tb_str = traceback.format_exc()
        except UnicodeDecodeError:
            friendly_str = 'Output contains non-printable characters'
            tb_str = traceback.format_exc()
        except OutputLimitExceeded:
            friendly_str = 'Program produced too much output (infinite loop?)'
            tb_str = traceback.format_exc()
        except OSError as e:
            friendly_str = 'OSError: ' + str(e)

        if (friendly_str):
            # Only if there was a failure. That way finding "test_err" in
            # <project>.json will only find real errors
            result['test_err'] = f' {friendly_str}\n'

        # Print as we go, for long running test cases
        result_str = format_pass_fail(result)
        if failed(result):
            print_red(result_str)

            # Print exception and traceback, if any
            if self.args.verbose:
                if friendly_str:
                    print_red(friendly_str, '\n')
                if tb_str:
                    last_line = tb_str.split('\n')[-2]
                    print_red(last_line, '\n')
        else:
            # Print passed test case
            print_green(result_str)

        return result


    def run_test_cases(self, repo_path):
        results = []
        if self.args.test_name is not None:
            for tc in self.test_cases:
                if tc.tc_cfg.name == self.args.test_name:
                    results.append(self.run_one_test(repo_path, tc))
        else:
            for tc in self.test_cases:
                results.append(self.run_one_test(repo_path, tc))
        return results


    # Build up the submission comment to send to Canvas
    def make_comment(self, repo_result):
        comment = ''
        if (self.build_err):
            comment += f'{self.build_err} '
        for result in repo_result['results']:
            comment += format_pass_fail(result)
            if result.get('test_err'):
                comment += f" {result['test_err']}"
        comment += self.make_earned_avail(repo_result)
        return comment


    # Build a string showing the points earned vs. available for this repo
    def make_earned_avail(self, repo_result):
        avail = self.total_rubric()
        ea = f"{repo_result['score']}/{avail}"
        if repo_result['late-penalty'] > 0:
           ea += f" late penalty: {repo_result['late-penalty']}"
        return ea 


    # Build and test one repo
    def test(self, repo):
        tc_results = []
        repo_path = repo.local
        student = repo.student
    
        repo_result = init_repo_result(student)

        if not os.path.isdir(repo_path):
            err = f'Local repo {repo_path} does not exist'
            repo_result['comment'] = err
            print_red(err, e='\n')
            return repo_result

        self.build_err = self.build(repo_path)
        if self.build_err:
            # Only if an error occurred. That way you can search
            # the <project>.json file for 'build_err' and find only real errors
            repo_result.update({
                'build_err': self.build_err
            })

        # Run the test cases
        tc_results = self.run_test_cases(repo_path)
        repo_result.update({
            'results'     : tc_results,
            'score'       : self.total_score(tc_results),
            'late-penalty': 0
        })
        self.apply_late_penalty(repo_result, repo.date)
        # Build the comment after applying any late penalty
        repo_result['comment'] = self.make_comment(repo_result)
        

        # Print net score for the repo
        print(self.make_earned_avail(repo_result))
        return repo_result


    def apply_late_penalty(self, repo_result, repo_date):
        if self.project_cfg.due_date and repo_date:
            # Due date is included in test case [project] section
            # Use ISO 8601 format for both so timedelta works
            delta = dt.fromisoformat(repo_date) - dt.fromisoformat(self.project_cfg.due_date)
            if delta.days >= 0:
                # Last commit date is later than due date
                # Calc penalty to two decimal places like Canvas
                penalty = round(repo_result['score'] * delta.days * 
                    self.project_cfg.late_penalty, 2)
                # delta has whole days and a fraction of a day so += 1
                penalty += 1
                repo_result['score'] -= penalty
                repo_result['late-penalty'] = penalty


    def total_score(self, results):
        score = 0;
        for r in results:
            score += r['score'];
        return score


    def total_rubric(self):
        total = 0
        for tc in self.test_cases:
            total += tc.tc_cfg.rubric
        return total


    # Print score frequency distribution
    def print_histogram(self, class_results):
        # Points available
        avail = self.total_rubric()
        # Sort class results by score, high to low
        class_results.sort(key=lambda repo_result: repo_result['score'], reverse=True)
        freqs = {}  # key: score, value: frequency
        for r in class_results:
            # Get score for one repo
            score = r['score']
            if not score in freqs:
                freqs[score] = 0
            freqs[score] += 1

        print(f'\nScore frequency (n = {len(class_results)})')
        for score, freq in freqs.items():
            pct = "{:.1f}".format(freq / len(class_results) * 100)
            print(f"{score}/{avail}: {freq}  ({pct}%)")
