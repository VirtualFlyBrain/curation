#!/usr/bin/env python3

import pandas as pd
import yaml
import glob
import re


def strip_file_extension(ext, filename):
    m = re.search("^(.+)\." + ext + "$", "filename")
    return m.group(1)

def get_recs(path_to_recs, spec_path):
    # Check _ Does glob preserve path?
    tsv_recs = glob.glob(path_to_recs + "*.tsv")
    yaml_recs = glob.glob(path_to_recs + "*.yaml")

    rec_names_from_yaml = [strip_file_extension("yaml", r) for r in yaml_recs]
    rec_names_from_tsv = [strip_file_extension("tsv", r) for r in tsv_recs]

    try: assert set(rec_names_from_yaml) == set(rec_names_from_tsv)
    except ValueError:
        print("Non matching records.")
        yaml_not_tsv = set(rec_names_from_yaml) - set(rec_names_from_tsv)
        if yaml_not_tsv:
            print("Yaml files without matching tsv %s" % str(yaml_not_tsv))
        tsv_not_yaml = set(rec_names_from_tsv) - set(rec_names_from_yaml)
        if tsv_not_yaml:
            print("tsv files without matching yaml %s" % str(tsv_not_yaml))
    else:
        rec_names = rec_names_from_tsv
        records = {}
        for r in rec_names:
            records[r] = Record(spec_path= spec_path,
                                 tsv_path= r + ".tsv",
                                 yaml_path= r + "*.yaml")

    return records


    # Test that every tsv file has a matching yaml file & vice_versa)


class Record(object):

    def __init__(self, spec_path, tsv_path, yaml_path):
        """path to tsv"""

        specfile = open(spec_path, "r")
        self.spec = yaml.load(specfile.read())
        specfile.close()
        self.tsv = pd.DataFrame.from_csv(tsv_path, sep = "\t")
        yfile = open(yaml_path, 'r')
        self.y = yaml.load(yfile.read())

    def check_working(self):
        self.check_tsv_headers()
        self.check_uniqueness()
        self.check_yaml_keys()

    def check_all(self):
        self.check_working()
        #Add more checks in here


# Should probably refactor to a single key check function.
    def check_tsv_headers(self):
        input_columns = set(self.tsv.Columns)
        # Allow for columns that are legal in YAML to be present in tsv.
        spec_columns = set(self.spec.keys())
        compulsory_columns = set([k for k in self.spec.keys if k['Compulsory']])

        try:
            assert input_columns == spec_columns
        except ValueError:
            illegal_columns = input_columns - spec_columns
            print("TSV contains illegal columns: %s" % str(illegal_columns))

        try:
            assert input_columns.issuperset(compulsory_columns)
        except ValueError:
            print("TSV is missing compulsory columns: %s" %
                    str(compulsory_columns - spec_columns))

    def check_yaml_keys(self):
        input_columns = set(self.y.keys())
        spec_columns = set([k for k in self.spec.keys()
                            if self.spec[k]['yaml']])
        compulsory_columns = set([k for k in self.spec.keys if k['Compulsory']])

        try:
            assert input_columns == spec_columns
        except ValueError:
            illegal_columns = input_columns - spec_columns
            print("YAML contains illegal keys: %s" % str(illegal_columns))

        try:
            assert input_columns.issuperset(compulsory_columns)
        except ValueError:
            print("YAML is missing compulsory keys: %s" %
                    str(compulsory_columns - spec_columns))

    def check_uniqueness(self):
        uniq_columns = [k for k in self.spec.keys if k['is_unique']]
        for c in uniq_columns:
            contents = list(self.tsv[c])
            s = set()
            duplicates = set(x for x in contents if x in s or s.add(x))
            try:
                assert duplicates is False
            except ValueError:
                print("Entries in Column %s should be uniq, but duplicate "
                      "entries found: %s" % (c, str(duplicates)))














