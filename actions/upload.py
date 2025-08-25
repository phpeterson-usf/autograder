import glob
import json
import os
from pathlib import Path
from simple_term_menu import TerminalMenu

from .util import fatal
from .canvas import Canvas, CanvasMapper


# Reconstitute 'grade class' results from previously-saved file
# This allows long-running test cases to be factored out
# of the upload process, which can also take some time
def upload_class(cfg, args):
    path = Path()
    if args.by_date:
        json_files = glob.glob('*.json')
        if not json_files:
            warn('No JSON files found')
            return
        menu = TerminalMenu(json_files)
        idx = menu.show()
        if idx is None:
            return
        path = json_files[idx]
    else:
        path = Path(args.project + '.json')

    try:
        with open(path) as f:
            data = f.read()
            class_results = json.loads(data)
        canvas = Canvas(cfg.canvas_cfg, args)
        mapper = CanvasMapper(cfg.canvas_mapper_cfg)
    except FileNotFoundError as fnf:
        fatal(f'{path} does not exist. Run "grade class -p {args.project}" first')

    for result in class_results:
        # Map GitHub username to Canvas SIS Login ID using imported CSV file
        login_id = mapper.lookup(result['student'])
        canvas.add_score(login_id, result['score'], result['comment'])
    canvas.upload()
