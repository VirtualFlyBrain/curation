#!/usr/bin/env python3

import logging
from vfb.curation.peevish import get_recs
from vfb.curation.curation_loader import load_recs
import argparse
import warnings
import os

"""
Script to
1. Check records in 'working/' for syntactic validity of names and files.
2. Test load records in 'to_submit/'.
"""
# What logic, if any should live here?
## Should it know about the gross type of records and direct to the appropriate loading method, where gross currently = new_dataSet vs new_metadata, vs new image.  Shouldn't a record sorter be able to do that?
 
# Argument parser setup
parser = argparse.ArgumentParser()
parser.add_argument("endpoint", help="Endpoint for connection to neo4J prod")
parser.add_argument("usr", help="username")
parser.add_argument("pwd", help="password")
parser.add_argument("--import_filepath", help="path to file usable for writing to DB via tsv", default='')
parser.add_argument("--base_path", help="Optional", default="../")
parser.add_argument("--test_mode", help="Optional", action='store_true', default=False)
parser.add_argument("--commit", help="Optional", action='store_true', default=False)
parser.add_argument("--verbose", help="Optional", action='store_true', default=False)
parser.add_argument("--allow_duplicates", help="Optional", action='store_true', default=False)
parser.add_argument("--debug", help="Enable debug logging", action='store_true', default=False)
args = parser.parse_args()

# Configure logging
if args.debug:
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
elif args.verbose:
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
else:
    logging.basicConfig(level=logging.WARNING, format='%(asctime)s - %(levelname)s - %(message)s')

def check_records(path, check_dir="working"):
    """
    Checks the records in the specified directory.
    
    Parameters:
    path (str): The base path to check records in.
    check_dir (str): The directory within the base path to check records in.
    
    Returns:
    bool: True if records pass the check, False otherwise.
    """
    try:
        logging.debug("Starting check_records with path: %s and check_dir: %s", path, check_dir)
        rec_path = '/'.join([args.base_path, path, check_dir]) + '/'
        logging.debug("Constructed rec_path: %s", rec_path)
        
        recs = get_recs(spec_path="../records/" + path, path_to_recs=rec_path)
        logging.debug("Retrieved records: %s", recs)
        
        stat = True
        if len(recs) == 0:
            logging.info("No records to check in: %s", rec_path)
        else:
            logging.info("Testing syntax of %s curation records.", len(recs))
        
        if False in recs:
            logging.warning("Some records failed the check.")
            stat = False
        
        return stat

    except Exception as e:
        logging.error("An error occurred in check_records: %s", e, exc_info=True)
        return False

def load_records(path, load_dir="to_submit"):
    """
    Loads the records from the specified directory.
    
    Parameters:
    path (str): The base path to load records from.
    load_dir (str): The directory within the base path to load records from.
    
    Returns:
    bool: True if records are successfully loaded, False otherwise.
    """
    try:
        logging.debug("Starting load_records with path: %s and load_dir: %s", path, load_dir)
        rec_path = os.path.abspath(os.path.join(args.base_path, path, load_dir))
        logging.debug("Constructed rec_path: %s", rec_path)
        
        current_dir = os.path.dirname(os.path.realpath(__file__))
        records_path = os.path.abspath(os.path.join(current_dir, "../records", path))
        logging.debug("Constructed records_path: %s", records_path)
        
        stat = load_recs(records_path + '/', rec_path + '/',
                         args.endpoint, args.usr, args.pwd, import_filepath=args.import_filepath,
                         commit=args.commit, verbose=args.verbose, allow_duplicates=args.allow_duplicates)
        
        logging.debug("load_recs returned status: %s", stat)
        return stat

    except Exception as e:
        logging.error("An error occurred in load_records: %s", e, exc_info=True)
        return False

stat = True

if not check_records(path="new_metadata/"): stat = False
if not load_records(path="new_metadata/"): stat = False
if not check_records(path="new_images/"): stat = False
if not load_records(path="new_images/"): stat = False
if not check_records(path="new_splits/"): stat = False
if not load_records(path="new_splits/"): stat = False

if not stat:
    raise Exception("Failing records. See preceding warnings for details.")
else:
    print("Success!")

if args.test_mode:
    print("Running record syntax fails tests")
    check_records(path="new_metadata/", check_dir="test_syntax_fail")
    check_records(path="new_images/", check_dir="test_syntax_fail")
    # check_records(path="new_splits/", check_dir="test_syntax_fail")

    print("Running fail tests.")
    load_records(path="new_metadata/", load_dir="test_load_fail")
    load_records(path="new_images/", load_dir="test_load_fail")
    # load_records(path="new_splits/", load_dir="test_load_fail")
