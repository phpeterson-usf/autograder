from pathlib import Path

from actions.util import SafeConfig, load_toml, fatal

"""
Example file format:

[project04]

[[project04.dates]]
date = "2025-03-18"
percentage = 1.0

[[project04.dates]]
date = "2025-03-25"
percentage = 0.5

"""
class Date(SafeConfig):
    """
    Date is an element of the Dates list, containing the due date and partial
    credit percentage for one delivery date
    """
    def __init__(self, cfg):
        self.date = 'YYYY-MM-DD'
        self.percentage = 0.0
        self.safe_update(cfg)


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
    
    @staticmethod
    def from_path(tests_path, args):
        # The due dates are expressed in tests/dates.toml, not in the test cases file
        dates_path = Path(tests_path) / 'dates.toml'
        try:
            table = load_toml(dates_path)
            project_dates = table[args.project]
            return Dates(project_dates['dates'], args.verbose)
        except FileNotFoundError as fnf:
            fatal(str(fnf))