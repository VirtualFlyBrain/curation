#!/usr/bin/env python3

import pandas as pd
# Hack fo get around different package name on pip vs condaForge
try:
    import ruamel_yaml
except:
    try:
        import ruamel.yaml as ruamel_yaml
    except:
        ImportError("Neither ruamel.yaml nor ruamel_yaml package found")
    pass
import glob
from collections import namedtuple, Counter
import warnings
import os
import logging


CurFile = namedtuple('CurFile', ['path', 'loc', 'extended_name',
                                 'name', 'ext', 'type', 'gross_type',
                                 'dataset', 'date'])

def process_file_path(file_path):
    path = [fp for fp in file_path.split('/') if fp]  # list comp removes empty path components (//)
    extended_name = path[-1]
    name_ext = extended_name.split('.')
    if not (len(name_ext) == 2):
        logging.warning("Can't parse filename extension for %s"
                        "Wrong number of '.'" % extended_name)
        return False
    name_breakdown = name_ext[0].split('_')
    if not (len(name_breakdown) == 3):
        logging.warning("Curation FileName (%s) has wrong format,"
                        "should be: type_dataset_date.ext" % extended_name)
        return False
    return CurFile(path=file_path,
                   loc=path[0],
                   extended_name=extended_name,
                   name=name_ext[0],
                   ext=name_ext[1],
                   type=name_breakdown[0],
                   gross_type=path[-3],
                   dataset=name_breakdown[1],
                   date=name_breakdown[2]
                   )


def get_recs(path_to_recs, spec_path):
    """path_to_recs = """

    ## This function knows nothing about content except what is in spec files.

    tsv_rec_files = glob.glob(path_to_recs + "*.tsv")
    yaml_rec_files = glob.glob(path_to_recs + "*.yaml")
    tsv_recs = [process_file_path(r) for r in tsv_rec_files]
    yaml_recs = [process_file_path(r) for r in yaml_rec_files]

    # Find pairs

    combined_recs = []
    if yaml_recs:
        yaml_rec_lookup = {y.name: y for y in yaml_recs}
    else:
        yaml_rec_lookup = {}

    for t in tsv_recs:
            if t.name in yaml_rec_lookup.keys():
                combined_recs.append((t, yaml_rec_lookup[t.name]))
            else:
                combined_recs.append((t,))

    records = []
    for r in combined_recs:
        rec = Record(spec_path=spec_path,
                     cur_recs=r)

        # Only return valid records
        if rec.stat:
            records.append(rec)
        else:
            # Not sure this is the best way to feed back up...
            records.append(False)
    return records


    # Test that every tsv file has a matching yaml file & vice_versa)


class Record:
    def __init__(self, spec_path, cur_recs):

        """spec path = *directory* where spec is located
        cur_recs = tuple of CurFile objects (tsv, potentially plus paired yaml)
         Attributes:
             self.spec: Curation spec for curation record type
             self.rel_spec: Spec with relations valid for curation & their ranges.
             self.tsv pandas.DataFrame of curation record - includes YAML curation file content as additional columns.
             self.cr = curRec object (curation file name breakdown)
             self.type = record type (from curRec - for convenience)
             self.gross_type = ross record type (from curRec - for convenience)
             self.y = data-structure of yaml curation partner to tsv
             self.stat: False if any checks have failed.  Use this to control
             exceptions in wrapper scripts
             """

        # This code is much messier than it needs to be!

        self.stat = True
        self.y = False
        with open(spec_path + '/' + cur_recs[0].type + '_spec.yaml', 'r') as type_spec_file:
            self.spec = ruamel_yaml.safe_load(type_spec_file.read())
            if os.path.isfile(spec_path + '/' + 'common_fields_spec.yaml'):
                with open(spec_path + '/' + 'common_fields_spec.yaml', 'r') as general_spec_file:
                    general_spec = ruamel_yaml.safe_load(general_spec_file.read())
                    self.spec.update(general_spec)
        with open(spec_path + '/' + 'relations_spec.yaml', 'r') as rel_spec_file:
            self.rel_spec = ruamel_yaml.safe_load(rel_spec_file.read())
        for cr in cur_recs:
            if cr.ext == 'tsv':
                self.tsv = pd.read_csv(cr.path, sep="\t")
                # self.tsv.fillna('', inplace=True)
                self.cr = cr
                self.type = self.cr.type
                self.gross_type = self.cr.gross_type
            elif cr.ext == 'yaml':
                y_file = open(cr.path, 'r')
                self.y = ruamel_yaml.safe_load(y_file.read())
            else:
                logging.warning("Unknown file type %s" % cr.extended_name)
                self.stat = False
        if self.y:
            self._proc_yaml()
            self.check_DataSet()
        self._check_headers()
        self.check_uniqueness()
        if self.stat:
            self.strip_unused_spec()

        # strip unused spec:
        #  for k in self.spec.keys()

    def strip_unused_spec(self):
        """Remove spec that doesn't correspond to any column header"""
        unused_spec = [k for k in self.spec.keys()
                       if k not in self.tsv.columns]
        for k in unused_spec:
            del self.spec[k]

    def _fail(self, test_name):
        logging.warning("%s failed test: %s" % (self.cr.path, test_name))
        self.stat = False


    def _proc_yaml(self):
        #  check all are literals first?
        for k,v in self.y.items():
            # Need to run spec check first.
            if k in self.spec.keys() and self.spec[k]['yaml']:
                self.tsv[k] = v
            else:
                self._fail("Yaml check")
                logging.warning("Record fail: %s Key not allowed in yaml: %s" % (k, self.cr.path))

# Should probably refactor to a single key check function.
    def _check_headers(self):
        input_columns = set(self.tsv.columns)
        # Allow for columns that are legal in YAML to be present in tsv.
        spec_columns = set(self.spec.keys())
        compulsory_columns = set([k for k, v in
                                  self.spec.items() if ('compulsory' in v.keys()) and v['compulsory']])


        #  Check all input columns in spec
        illegal_columns = input_columns - spec_columns
        if illegal_columns:
            self._fail("TSV header test")
            warnings.warn("TSV contains illegal columns: %s" % str(illegal_columns))

        if not input_columns.issuperset(compulsory_columns):
            self._fail("TSV header test")
            warnings.warn("TSV is missing compulsory columns: %s" %
                  str(compulsory_columns - input_columns))


    def check_uniqueness(self):
        uniq_columns = [k for k, v in self.spec.items() if 'uniq' in v.keys() and v['uniq']]
        for c in uniq_columns:
            # This will fail unless NaN is converted to empty string to cope with empty cells.
            if c in self.tsv.columns:
                contents = list(self.tsv[c].dropna())
                duplicates = [item for item, count
                            in Counter(contents).items() if count > 1]
                if len(duplicates):
                    self._fail("Column uniqueness test")
                    warnings.warn("Entries in Column %s should be uniq, "
                                  "but duplicate "
                                  "entries found: %s" % (c, str(duplicates)))

    def check_DataSet(self):
        if 'dataset' in self.y.keys():
            if not self.y.dataset == self.cr.dataset:
                self._fail("DataSet test")
                warnings.warn("dataset specified in yaml (%s doesn't match that "
                          "in name %s" % (self.y.dataset,
                                          self.cr.dataset))




















