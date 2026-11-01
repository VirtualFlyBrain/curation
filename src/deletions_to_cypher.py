#!/usr/bin/env python3
"""Print the Cypher that a newmeta_deletions record will run, for review.

  python deletions_to_cypher.py ../records/newmeta_deletions/to_submit/deletions_X_YYMMDD.tsv [...]

Prints DELETE statements by default; --check prints the read-only versions
the Test job runs. Rows that can't be converted are reported on stderr.
"""
import argparse
import os
import sys

import pandas as pd

from vfb.curation.deletion_cypher import deletion_statements
from vfb.curation.peevish import ruamel_yaml

here = os.path.dirname(os.path.realpath(__file__))
parser = argparse.ArgumentParser()
parser.add_argument("tsv", nargs="+", help="deletions TSV file(s)")
parser.add_argument("--check", action="store_true", help="print read-only (count) statements")
parser.add_argument("--relations", default=os.path.join(here, "../records/new_metadata/relations_spec.yaml"))
args = parser.parse_args()

with open(args.relations) as f:
    relations = ruamel_yaml.safe_load(f).keys()

failed = False
for path in args.tsv:
    rows = pd.read_csv(path, sep="\t", dtype=str).fillna('').to_dict('records')
    statements, failures = deletion_statements(rows, relations, delete=not args.check)
    print("// %s: %d statement(s)" % (path, len(statements)))
    for _, s in statements:
        print(s + ";")
    for f in failures:
        failed = True
        print("%s: [%s] %s :: %s" % (path, f['context_name'], f['message'], f['context']), file=sys.stderr)

sys.exit(1 if failed else 0)
