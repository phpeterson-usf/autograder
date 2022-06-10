#!/usr/bin/env python3

import csv
from pathlib import Path
import requests
import sys
from tomlkit import parse
from tomlkit import dumps

from actions.config import config_path, config_temp_path

# Download list of students from a Google Sheets spreadsheet
# ss_id: document ID out of the URL, e.g. "1Nj4Lvldz_94PlHmRUrSfl_5rm6tgm5JnkCob-p63PGk"
# ss_name: name of the spreadsheet tab
# Returns the CSV reader obj for the caller to iterate
def _download(ss_id, ss_name):
    url = 'https://docs.google.com/spreadsheets/d/{}/gviz/tq?tqx=out:csv&sheet={}'\
        .format(ss_id, ss_name)
    response = requests.get(url)
    if response.status_code != requests.codes.ok:
        print('requests.get returned {}', response.status_code)
        sys.exit(-1)

    return csv.DictReader(response.text.splitlines())

# Rewrite config.toml with the given list of student GitHub usernames 
def _update(students):
    # Read the old config file
    doc = None
    path = config_path()
    try:
        with open(path, 'r') as f:
            doc = parse(f.read())

        # Write the new config file to a temp path
        temp_path = config_temp_path()
        with open(temp_path, 'w') as t:
            # tomlkit helpfully provides random access to elements of the TOML
            # document while preserving the comments
            if doc.get('students'):
                doc.remove('students')
            doc['students'] = students
            t.write(dumps(doc))

        # Replace the old file with the new one. The order is right, I swear!
        temp_path.replace(path)
    except Exception as e:
        print(str(e))


# Public API to import the list of students and store them
def import_students(ss_id, tab_name):
    students = []
    reader = _download(ss_id, tab_name)
    for row in reader:
        students.append(row['GitHub'])
    return students

    if students:
        _update(students)


# Test harness
if __name__ == "__main__":
    import_students(sys.argv[1], sys.argv[2])
