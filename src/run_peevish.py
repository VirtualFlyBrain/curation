#!/usr/bin/env python3

from vfb.curation.peevish import get_recs
from vfb.curation.curation_loader import load_recs
#from vfb.curation.cur_load import NewMetaDataWriter, NewImageWriter
import argparse
import warnings

"""
Script to
1. Check records in 'working/' for syntactic validity of names and files.
2. Test load records in 'to_submit/'.
"""
# What logic, if any should live here?

## Should it know about the gross type of records and direct to the appropriate loading method, where gross currently = new_dataSet vs new_metadata, vs new image.  Shouldn't a record sorter be able to do that?


parser = argparse.ArgumentParser()
parser.add_argument("endpoint",
                    help="Endpoint for connection to neo4J prod")
parser.add_argument("usr",
                    help="username")
parser.add_argument("pwd",
                    help="password")
parser.add_argument("--base_path", help="Optional", default="../")
parser.add_argument("--test_mode", help="Optional", action='store_true', default=False)
args = parser.parse_args()



def check_records(path, check_dir = "working"):
    rec_path = '/'.join([args.base_path, path, check_dir]) + '/'
    recs = get_recs(spec_path="../records/" + path,
                    path_to_recs=rec_path)
    stat = True
    if len(recs) == 0:
        print("No records to check in: " + rec_path)
    else:
        print("Testing syntax of %s curation records." % len(recs))
    if False in recs:
        stat = False
    return stat



def load_records(path, load_dir = "to_submit"):
    rec_path = '/'.join([args.base_path, path, load_dir]) + '/'
    stat = load_recs("../records/" + path, rec_path, args.endpoint, args.usr, args.pwd)
    return stat


stat = True

if not check_records(path="new_images/"): stat = False
if not load_records(path="new_images/"): stat = False

#if not check_records(path="new_datasets/"): stat = False

if not check_records(path="new_metadata/"): stat = False
if not load_records(path="new_metadata/"): stat = False

if not stat:
    raise Exception("Failing records. See preceding warnings for details.")
else:
    print("* Test loading succeeded for all records * ")

if args.test_mode:
    print("*** Running record syntax fails tests ***")
    check_records(path="new_metadata/", check_dir="test_syntax_fail")
    print("*** Running fail tests.***")
    load_records(path="new_metadata/", load_dir="test_load_fail")

