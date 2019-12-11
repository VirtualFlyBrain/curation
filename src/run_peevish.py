#!/usr/bin/env python3

from vfb.curation.peevish import get_recs
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
args = parser.parse_args()



def check_records(path):
    rec_path = '/'.join([args.base_path, path, "working"]) + '/'
    recs = get_recs(spec_path="../records/" + path,
                    path_to_recs=rec_path)
    stat = True
    if len(recs) == 0:
        warnings.warn("No records to check in: " + rec_path)
    if False in recs:
        stat = False
    return stat



def load_records(path, loader_class):
    rec_path = '/'.join([args.base_path, path, "to_submit"]) + '/'
    recs = get_recs(spec_path="../records/" + path,
                    path_to_recs=rec_path)
    stat = True
    if len(recs) == 0:
        warnings.warn("No records to check in: " + rec_path)
    for r in recs:
        if r:
            loader = loader_class(args.endpoint, args.usr, args.pwd, r)
            loader.write()
        else:
            stat = False
    return stat


stat = True

if not check_records(path="new_images/"):
    stat = False
#if not check_records(path="new_datasets/"):
#    stat = False
if not check_records(path="new_metadata/"):
    stat = False

# load_records(path="../records/new_images", loader_class=NewImageWriter)
# load_records(path="../records/new_metadata", loader_class=NewMetaDataWriter)

if not stat:
    raise Exception("Failing records.  See preceding warnings for details.")


