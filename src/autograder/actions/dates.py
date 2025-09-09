from pathlib import Path

from .util import SafeConfig, load_toml, fatal

"""
Example file format:

[project04]

[[project04.dates]]
suffix = "due"
date = "2025-03-11"
percentage = 1.0

[[project04.dates]]
suffix = "late1wk"
date = "2025-03-18"
percentage = 0.5
"""

class Date(SafeConfig):
    """
    Date is an element of the Dates list, containing the name, due date, 
    and partial credit percentage for one delivery date
    """
    def __init__(self, cfg):
        self.suffix = ''
        self.date = 'YYYY-MM-DD'
        self.percentage = 0.0
        self.safe_update(cfg)
        self.suffix.replace(' ', '-')   # a little extra safety for dir name


class Dates:
    """
    Dates is the list of milestones that students can get full or partial credit
    for turning in work by the given date
    """
    def __init__(self, dates, verbose):
        self.dates = []
        self.verbose = verbose
        for date in dates:
            if self.verbose:
                print(date)
            self.dates.append(Date(date))

    def select_date(self):
        from simple_term_menu import TerminalMenu
        options = [d.suffix + ' ' + d.date for d in self.dates]
        terminal_menu = TerminalMenu(options)
        idx = terminal_menu.show()
        if idx is None:
            return None
        return self.dates[idx]

    @staticmethod
    def from_path(tests_path, args):
        """
        from_path() loads the TOML content of the dates.toml file. Due dates 
        were previously given in the test case TOML file, but now are split
        into a separate file which changes every semester
        """
        dates_path = Path(tests_path) / 'dates.toml'
        try:
            table = load_toml(dates_path)
            if not table:
                fatal(f'File not found: {dates_path})')
            project_dates = table[args.project]
            return Dates(project_dates['dates'], args.verbose)
        except FileNotFoundError as fnf:
            fatal(str(fnf))
