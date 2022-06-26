import difflib
import json
import os
import pprint

from actions.cmd import cmd_exec_capture, cmd_exec_rc
from actions.util import failed, fatal, format_pass_fail, load_toml, print_green, print_red


# One test case out of the list in the TOML test case file
class TestCase:

    @staticmethod
    def from_cfg(tc_cfg, project_cfg, args):
        tc = json.loads(json.dumps(tc_cfg), object_hook=TestCase)
        tc.args = args  # need verbose, project
        tc.project_cfg = project_cfg  # need strip_output
        return tc


    def __init__(self, tc_cfg):
        self.output = 'stdout' # default

        self.__dict__.update(tc_cfg)
        self.args = None
        self.project_cfg = None
        self.cmd_line = []
        self.validate(tc_cfg)


    def validate(self, d):
        test_name = d.get('name', 'unknown')
        if type(d.get('rubric')) is not int:
            fatal('Rubric for test \"{test_name}\" must be an integer')
        if type(d.get('input')) is not list:
            fatal(f'Input for test \"{test_name}\" must be a list')
        if type(d.get('expected')) is not str:
            fatal(f'Expected output for test \"{test_name}\" must be a string')


    def init_cmd_line(self, digital_path, project_tests_path):
        for i in self.input:
            if '$project_tests' in i:
                param = i.replace('$project_tests', project_tests_path)
            elif '$project' in i:
                param = i.replace('$project', self.args.project)
            elif '$digital' in i:
                param = i.replace('$digital', digital_path)
            else:
                param = i
            self.cmd_line.append(param)


    def get_actual(self, local):
        if self.output == 'stdout':
            # get actual output from stdout
            act = cmd_exec_capture(self.cmd_line, local)
        else:
            # ignore stdout and get actual output from the specified file
            path = os.path.join(local, self.output)
            act = cmd_exec_capture(self.cmd_line, local, path)

        if self.project_cfg.get('strip_output'):
            act = act.replace(self.project_cfg['strip_output'], '')
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
        for line in text.split('\n'):
            text_lines.append(line.strip() + '\n')
        return text_lines
        
    def match_expected(self, actual):
        # rstrip to remove extra trailing newline
        exp = self.make_lines(self.expected.rstrip())
        act = self.make_lines(actual.rstrip())

        cmd_line = self.prepare_cmd_line(self.cmd_line)
        cmd_line_str = ' '.join(cmd_line)

        if self.args.very_verbose:
            print(f"===[{self.name}]===expected\n$ {cmd_line_str}\n{exp}")
            print()
            print(f"===[{self.name}]===actual\n$ {cmd_line_str}\n{act}")
            print()
        if self.args.verbose and (act != exp):
            print(f"===[{self.name}]===diff\n$ {cmd_line_str}")
            diff = difflib.context_diff(exp, act, fromfile='expected', tofile='actual')
            for line in diff:
                print(line, end='')
            print()

        return act == exp


class Test:
    default_cfg = {
        'tests_path': '~/tests',
        'digital_path': '~/Digital/Digital.jar'
    }

    @staticmethod
    def from_cfg(test_cfg, args):
        # Create a Test object from the test_cfg dict
        test = json.loads(json.dumps(test_cfg.__dict__), object_hook=Test)
        test.args = args
        test.load_test_cases()
        return test


    def __init__(self, cfg):
        self.__dict__.update(cfg)
        self.tests_path = os.path.expanduser(self.tests_path)
        self.digital_path = os.path.expanduser(self.digital_path)
        self.args = None
        self.project_cfg = {
            'build': 'make',
            'strip_output': None,
        }
        self.test_cases = []


    def load_test_cases(self):
        # Load <project>.toml
        path = os.path.join(
            self.tests_path,
            self.args.project,
            self.args.project + '.toml'
        )
        toml_doc = load_toml(path)

        # Load the [project] table which contains project-specific config
        project_cfg = toml_doc.get('project', {})
        self.project_cfg.update(project_cfg)

        # Create test cases for each element of the [tests] table
        project_tests_path = os.path.join(self.tests_path, self.args.project)
        for tc_cfg in toml_doc['tests']:
            tc = TestCase.from_cfg(tc_cfg, project_cfg, self.args)
            tc.init_cmd_line(self.digital_path, project_tests_path)
            self.test_cases.append(tc)


    def build(self, repo_path):
        b = self.project_cfg['build']
        if b == 'none':
            return
        if b == 'make':
            try:
                cmd_exec_rc(['make', '-C', repo_path])
            except Exception as e:
                print_red(str(e), '\n')
        else:
            fatal(f'Unknown build plan: \"{b}\"')


    def run_one_test(self, repo_path, test_case):
        score = 0
        actual = test_case.get_actual(repo_path)
        if test_case.match_expected(actual):
            score = test_case.rubric

        # Record score for later printing/uploading
        result = {'test': test_case.name, 'score': score}

        # Print as we go, for long running test cases
        s = format_pass_fail(result)
        if failed(result):
            print_red(s)
        else:
            print_green(s)

        return result


    def run_test_cases(self, repo_path):
        results = []
        if self.args.test_name is not None:
            for tc in self.test_cases:
                if tc.name == self.args.test_name:
                    results.append(self.run_one_test(repo_path, tc))
        else:
            for tc in self.test_cases:
                results.append(self.run_one_test(repo_path, tc))
        return results


    # Build up the submission comment to send to Canvas
    def make_comment(self, tc_results):
        comment = ''
        for result in tc_results:
            comment += format_pass_fail(result)
        return comment


    # Build and test one repo
    def test(self, student, repo_path):

        self.build(repo_path)
        tc_results = self.run_test_cases(repo_path)
        repo_result = {
            'student': student,
            'results': tc_results,
            'comment': self.make_comment(tc_results),      
            'score': self.total_score(tc_results),
        }

        # Print net score for the repo
        earned = self.total_score(tc_results)
        avail = self.total_rubric()
        print(f"{earned}/{avail}")

        return repo_result


    def total_score(self, results):
        score = 0;
        for r in results:
            score += r['score'];
        return score


    def total_rubric(self):
        total = 0
        for tc in self.test_cases:
            total += tc.rubric
        return total


    # Print score frequency distribution
    def print_histogram(self, class_results):
        # Points available
        avail = self.total_rubric()
        # Sort class results by score, high to low
        class_results.sort(key=lambda x: self.total_score(x['results']), reverse=True)
        freqs = {}  # key: score, value: frequency
        for r in class_results:
            # Get score for one repo
            score = self.total_score(r['results'])
            if not score in freqs:
                freqs[score] = 0
            freqs[score] += 1

        print("\nScore frequency")
        for score, freq in freqs.items():
            pct = "{:.1f}".format(freq / len(class_results) * 100)
            print(f"{score}/{avail}: {freq}  ({pct}%)")