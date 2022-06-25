#!/usr/bin/env python3

import csv
import json
from pathlib import Path
import requests
import sys
from tomlkit import dumps, parse

from actions.util import config_path, config_temp_path

class Importer:
    default_cfg = {
        'doc_id': 'your Google Doc ID here',
        'sheet_name': 'Sheet 1',
        'github_col_name': 'GitHub',
    }


    def from_cfg(imp_cfg):
        return json.loads(json.dumps(imp_cfg.__dict__), object_hook=Importer)

    def __init__(self, imp_cfg):
        self.__dict__.update(imp_cfg)


    def import_students(self):
        students = []
        reader = self.download()
        for row in reader:
            students.append(row[self.github_col_name])
        if students:
            self.rewrite(students)

    # Download list of students from a Google Sheets spreadsheet
    def download(self):
        url = 'https://docs.google.com/spreadsheets/d/{}/gviz/tq?tqx=out:csv&sheet={}'\
            .format(self.doc_id, self.sheet_name)

        response = requests.get(url)
        if response.status_code != requests.codes.ok:
            print('requests.get returned {}', response.status_code)
            sys.exit(-1)

        return csv.DictReader(response.text.splitlines())

    # Rewrite config.toml with the given list of student GitHub usernames 
    def rewrite(self, students):
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
                table = doc.get('Config')
                if table.get('students'):
                    table.remove('students')
                table['students'] = students
                t.write(dumps(doc))

            # Replace the old file with the new one. The order is right, I swear!
            temp_path.replace(path)
        except Exception as e:
            print(str(e))




"""
# Test harness
if __name__ == "__main__":
    import_students(sys.argv[1], sys.argv[2])
"""
