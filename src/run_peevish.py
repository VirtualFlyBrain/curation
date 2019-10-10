#!/usr/bin/env python3

from .peevish import get_recs
import warnings
import sys


def check_working(path):
    recs = get_recs(spec_path=path + "spec.yaml", path_to_recs=path + "working")
    for k,v in recs.items():
        print("Checking %s" % k)
        v.check_working()


check_working(path="../../../records/new_images")

#run_type = sys.argv[1]
#path = sys.argv[2]
#if run_type == "--working":
#    check_working(path)
#else:
#    warnings.warn("Unknown arg")

