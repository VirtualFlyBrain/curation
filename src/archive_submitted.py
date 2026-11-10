#!/usr/bin/env python3
"""Move loaded records from the to_submit folders to records/archive (git mv).

Run from a curator branch after a successful Run job, then commit and push:

  python src/archive_submitted.py            # all to_submit folders
  python src/archive_submitted.py --dry-run  # list what would move

Only .tsv/.yaml record files move; READMEs stay. Refuses to overwrite a file
already in the archive.
"""
import argparse
import glob
import os
import subprocess
import sys

records = os.path.abspath(os.path.join(os.path.dirname(os.path.realpath(__file__)), "../records"))
parser = argparse.ArgumentParser()
parser.add_argument("--dry-run", action="store_true")
args = parser.parse_args()

files = sorted(f for ext in ("tsv", "yaml")
               for f in glob.glob(os.path.join(records, "*", "to_submit", "*." + ext)))
if not files:
    print("Nothing in to_submit.")
    sys.exit(0)

clashes = [f for f in files if os.path.exists(os.path.join(records, "archive", os.path.basename(f)))]
if clashes:
    sys.exit("Already in archive, not moving anything:\n  " + "\n  ".join(clashes))

for f in files:
    print(os.path.relpath(f, records), "-> archive/")
    if not args.dry_run:
        subprocess.run(["git", "mv", f, os.path.join(records, "archive")], check=True, cwd=records)

if not args.dry_run:
    print("Moved %d file(s); commit and push the branch." % len(files))
