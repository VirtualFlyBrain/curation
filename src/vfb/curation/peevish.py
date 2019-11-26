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
from .cur_load import CurationWriter, Annotate


CurFile = namedtuple('CurFile', ['path', 'loc', 'extended_name',
                                 'name', 'ext', 'type',
                                 'dataset', 'date'])

def process_file_path(file_path):
    path = file_path.split('/')
    extended_name = path[-1]
    name_ext = extended_name.split('.')
    if not (len(name_ext) == 2):
        warnings.warn("Can't parse filename extension for %s"
                      "Wrong number of '.'" % extended_name)
        return False
    name_breakdown = name_ext[0].split('_')
    if not (len(name_breakdown) == 3):
        warnings.warn("Curation FileName (%s) has wrong format,"
                      "should be: type_dataset_date.ext" % extended_name)
        return False
    return CurFile(path=file_path,
                   loc=path[0],
                   extended_name=extended_name,
                   name=name_ext[0],
                   ext=name_ext[1],
                   type=name_breakdown[0],
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
        records.append(Record(spec_path=spec_path,
                              cur_recs=r))

    return records


    # Test that every tsv file has a matching yaml file & vice_versa)


class Record:
    # Architecture question: Raise exceptions, or warn and return false
    # so that wrapper script can check all recs?  Probably latter.

    def __init__(self, spec_path, cur_recs):

        """spec path = *directory* where spec is located
        cur_recs = tuple of CurFile objects (tsv, potentially plus paired yaml)
         Attributes:
             self.spec: Curation spec for curation record type
             self.tsv pandas.DataFrame of curation record
             self.cr = curRec object (curation file name breakdown)
             self.y = datastrucure of yaml curation partner to tsv
             """
        stat = True
        with open(spec_path + cur_recs[0].type + '_spec.yaml', 'r') as type_spec_file:
            with open(spec_path + 'common_fields_spec.yaml', 'r') as general_spec_file:
                self.spec = ruamel_yaml.safe_load(type_spec_file.read())
                general_spec = ruamel_yaml.safe_load(general_spec_file.read())
                self.spec.update(general_spec)
        with open(spec_path + 'relations_spec.yaml', 'r') as rel_spec_file:
            self.rel_spec = ruamel_yaml.safe_load(rel_spec_file.read())
        for cr in cur_recs:
            if cr.ext == 'tsv':
                self.tsv = pd.read_csv(cr.path, sep="\t")
                self.cr = cr
            elif cr.ext == 'yaml':
                y_file = open(cr.path, 'r')
                self.y = ruamel_yaml.safe_load(y_file.read())
            else:
                warnings.warn("Unknown file type %s" % cr.extended_name)
                stat = False
        stat = self._check_headers()
        stat = self._proc_yaml()


    def _proc_yaml(self):
        #  check all are literals first?
        for k,v in self.y.items():
            # Need to run spec check first.
            if self.spec[k]['yaml']:
                self.tsv[k] = v
            else:
                warnings.warn("Key not allowed in yaml: %s" % k)

# Should probably refactor to a single key check function.
    def _check_headers(self):
        input_columns = set(self.tsv.columns).union(set(self.y.keys()))
        # Allow for columns that are legal in YAML to be present in tsv.
        spec_columns = set(self.spec.keys())
        compulsory_columns = set([k for k, v in
                                  self.spec.items() if v['compulsory']])


        #  Check all input columns in spec
        try:
            assert not (input_columns - spec_columns)
        except ValueError:
            illegal_columns = input_columns - spec_columns
            print("TSV contains illegal columns: %s" % str(illegal_columns))

        try:
            assert input_columns.issuperset(compulsory_columns)
        except ValueError:
            print("TSV is missing compulsory columns: %s" %
                  str(compulsory_columns - spec_columns))


    def check_uniqueness(self):
        uniq_columns = [k for k, v in self.spec.items() if 'uniq' in v.keys() and v['uniq']]
        for c in uniq_columns:
            # Need to strip Nan - to cope with empty rows!
            contents = list(self.tsv[c].dropna())
            duplicates = [item for item, count
                          in Counter(contents).items() if count > 1]
            try:
                assert len(duplicates) == 0
            except ValueError:
                Exception("Entries in Column %s should be uniq, but duplicate "
                      "entries found: %s" % (c, str(duplicates)))

    def check_DataSet(self):
        if 'dataset' in self.y.keys():
            try:
                assert self.y.dataset == self.cr.dataset
            except ValueError:
                Exception("dataset specified in yaml (%s doesn't match that "
                          "in name %s" % (self.y.dataset,
                                          self.cr.dataset))


# Should probably move following to separate file:

















