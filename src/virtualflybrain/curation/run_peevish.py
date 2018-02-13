#!/usr/bin/env python3

from .peevish import get_recs

def check_working(path):
    recs = get_recs(spec_path=path + "spec.yaml", path_to_recs=path + "working")
    for k,v in recs.item():
        print("Checking %s" % k)
        v.check_working()
