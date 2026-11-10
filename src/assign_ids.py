#!/usr/bin/env python3
"""Assign VFB ids to new image rows before they are loaded.

For every records/new_images/to_submit/*.tsv, each row with an empty anat_id gets the next free VFB_ id (whose VFBc_
channel id is also free), starting at the record's yaml Start. The ids are reserved in the KB as :IdReservation nodes,
so no other loader mints them, and written into the tsv's anat_id column (added if missing). Commit the changed tsvs
before loading: a retry then reuses the same ids, and rows already loaded are skipped (NewImageWriter).
Only the anat_id column changes; every other byte of the file is kept.

Prints the changed files, one per line. Stops with a non-zero exit at the first file whose ids cannot be loaded or
reserved (files already done keep their ids; the reservations of a run that is not committed are only wasted ids).
"""
import argparse
import glob
import os
import sys

import ruamel.yaml as ruamel_yaml
from uk.ac.ebi.vfb.neo4j.KB_tools import KB_pattern_writer


def read_rows(path):
    with open(path, newline='') as f:
        text = f.read()
    nl = '\r\n' if '\r\n' in text else '\n'
    lines = text.split(nl)
    return lines, nl


def assign(path, pw, reserved_for):
    lines, nl = read_rows(path)
    header = lines[0].split('\t')
    if 'anat_id' in header:
        col = header.index('anat_id')
    else:
        col = len(header)
        lines[0] = lines[0] + '\tanat_id'
    todo = []
    for i, line in enumerate(lines[1:], 1):
        if not line.strip():
            continue
        cells = line.split('\t')
        if col >= len(cells) or not cells[col].strip():
            todo.append(i)
    if not todo:
        return False
    yml = os.path.splitext(path)[0] + '.yaml'
    start = '100000'
    if os.path.exists(yml):
        with open(yml) as f:
            y = ruamel_yaml.safe_load(f.read()) or {}
        start = str(y.get('Start', start))
    ids = pw.reserve_image_ids(start, len(todo), reserved_for + ':' + os.path.basename(path))
    for i, sf in zip(todo, ids):
        cells = lines[i].split('\t')
        cells += [''] * (col + 1 - len(cells))
        cells[col] = sf
        lines[i] = '\t'.join(cells)
    with open(path, 'w', newline='') as f:
        f.write(nl.join(lines))
    print("%s: %d id(s) %s..%s" % (path, len(ids), ids[0], ids[-1]), file=sys.stderr)
    return True


def main():
    p = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    p.add_argument("endpoint")
    p.add_argument("usr")
    p.add_argument("pwd")
    p.add_argument("--base_path", default="../records", help="records directory")
    p.add_argument("--reserved_for", default="curation", help="who the ids are reserved for, e.g. the branch")
    a = p.parse_args()
    files = sorted(glob.glob(os.path.join(a.base_path, 'new_images', 'to_submit', '*.tsv')))
    if not files:
        return
    pw = KB_pattern_writer(a.endpoint, a.usr, a.pwd, use_base36=True)
    for path in files:
        if assign(path, pw, a.reserved_for):
            print(path)


if __name__ == '__main__':
    main()
