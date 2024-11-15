from uk.ac.ebi.vfb.neo4j.neo4j_tools import results_2_dict_list
from dataclasses import dataclass
from typing import List
from uk.ac.ebi.vfb.neo4j.neo4j_tools import escape_string as escape_string_for_neo
from uk.ac.ebi.vfb.neo4j.KB_tools import kb_owl_edge_writer, KB_pattern_writer
from uk.ac.ebi.vfb.neo4j.flybase2neo.feature_tools import FeatureMover
from uk.ac.ebi.vfb.neo4j.flybase2neo.feature_tools import split
from uk.ac.ebi.vfb.neo4j.flybase2neo.pub_tools import pubMover
from .peevish import Record
import numpy
import logging
import warnings
import re
import time
from datetime import datetime, timedelta


@dataclass
class VfbInd:
    """VFB individual. Must have attributes:
       *name* (label) + *ID* (short_form)
    OR
       *xref_db* (external db/site short_form) + *xref_acc* (external id)
        (optionally including label).
    *_stat* is an auto-generated validation status marker.
    Any assigned value will be over-writen
    """
    label: str = ''
    id: str = ''
    xref_db: str = ''
    xref_acc: str = ''
    _stat: bool = True

    def __post_init__(self):
        if type(self.xref_acc) is float: self.xref_acc = int(self.xref_acc)
        self.validate()

    def validate(self):
        """Must have either label + id OR xref
          xref must contain a single colon"""
        if self.xref_acc:
            if not self.xref_db:
                warnings.warn("External accession provided but no database: "
                              "%s" % self.__str__())
                self._stat = False
            if self.id:
                warnings.warn("ID and xref provided, Which do you want me to use?"
                          "%s" % (self.__str__()))
                self._stat = False
        elif self.id:
            if not self.label:
                warnings.warn("ID provided (%s) but no label. "
                              "Please provide a label "
                              "(name) to go with this ID for cross-checking."
                              "" % self.id)
                self._stat = False
        else:
            logging.warning('Not enough information supplied to identify subject. Minimum =  dbxref or ID, you supplied only %s' % self.__str__())

            self._stat = False

@dataclass  # post init step addition of attribute prevents adding frozen=True
class LConf:
    """field = node attribute  to which regex restriction applies"""
    field: str
    regex: str
    labels: List[str]

    def __post_init__(self):
        if self.labels:
            self.neo_label_string = ':' + ':'.join(self.labels)
        else:
            self.neo_label_string = ''

class CurationWriter:
    """A wrapper class for loading annotation curation tables to VFB KB"""

    def __init__(self, endpoint, usr, pwd, record: Record, import_file_path=''):
        """KB connection: endpoint, usr, pwd
        lookup_config: a dict of lists of LookupConf keyed on column name or relation name.
        relation_lookup: name: short_form dictionary for valid relations"
        """

        # TBD: how to deal with FB features.  Maybe needs to be outside of this by adding to
        # KB first?
        self.pattern_writer = KB_pattern_writer(endpoint, usr, pwd, use_base36=True) # maybe limit this to NewImageWriter
        self.feature_mover = FeatureMover(endpoint, usr, pwd, file_path=import_file_path)
        self.pub_mover = pubMover(endpoint, usr, pwd)
        self.ew = self.feature_mover.ew
        self.record = record
        self.object_lookup = self.generate_object_lookups()
        self.relation_lookup = self.generate_relation_lookup()
        self.stat = True
        logging.info(f"CurationWriter initialized for record: {record.cr.path}")

    def warn(self, context_name, context, message, stat=False):
        logging.warning("Error in record %s, %s\n %s\n:"
                        "" % (self.record.cr.name, context_name,
                              str(context)) + message)
        if not stat:
            self.stat = False

    def generate_object_lookups(self):
        cl = self._generate_lookups(self._gen_lookup_config_by_header())
        rl = self._generate_lookups(self._gen_lookup_config_by_rel())
        cl.update(rl)  # Might be better to have these as separate lookups?
        return cl  # return not being used?

    def _gen_lookup_config_by_rel(self):
        return {k: [LConf(field=v['restriction']['field'],
                   regex=v['restriction']['regex'],
                   labels=v['restriction']['labels'])]
                for k, v in self.record.rel_spec.items()
                if 'restriction' in v.keys()}

    def _gen_lookup_config_by_header(self):
        return {k: [LConf(field=v['restriction']['field'],
                   regex=v['restriction']['regex'],
                   labels=v['restriction']['labels'])]
                for k, v in self.record.spec.items()
                if 'restriction' in v.keys()}

    def generate_relation_lookup(self):
        return {k: v['short_form']
                for k, v in self.record.rel_spec.items()
                if not (k == 'is_a')}  # Not keen on hard wiring here, but maybe unavoidable

    def _generate_lookups(self, conf):
        """Generate :Class name:ID lookups from DB for loading by label.
        Lookups are defined by standard config that specifies a config:
        name:field:regex, e.g. {'part_of': {'short_form': 'FBbt_.+'}}
        name should match the kwarg for which it is to be used.
        """
        lookup_config = conf
        lookup = {}
        if lookup_config:
            for name, lcs in lookup_config.items():
                lookup[name] = {}
                queries = []
                for c in lcs:
                    q = "MATCH (c%s) where c.%s =~ '%s' RETURN c.label as label, c.short_form as short_form" % (c.neo_label_string, c.field, c.regex)
                    queries.append(q)
                # Execute queries in batches
                results = self.ew.nc.commit_list(queries)
                if isinstance(results, str):
                    logging.error(f"Unexpected result type: {results}")
                    raise TypeError(f"Expected list of dicts but got string: {results}")
                # Process results
                r_dict = results_2_dict_list(results)
                lookup[name].update({escape_string_for_neo(x['label']): x['short_form'] for x in r_dict})
        return lookup

    def extend_lookup_from_flybase(self, features, key='expresses'):
        fu = "('"+"', '".join(features) + "')"
        query = "SELECT f.uniquename AS short_form, f.name AS label" \
                " FROM feature f WHERE f.name IN %s" \
                " AND f.is_obsolete is FALSE"% fu
        dc = self.feature_mover.query_fb(query)
        self.object_lookup[key] = {escape_string_for_neo(d['label']): d['short_form'] for d in dc}

    def write_rows(self, verbose=False, start='100000', allow_duplicates=False):
        start_time = time.time()
        tot = len(self.record.tsv)
        batch_size = 1000  # Set batch size
        # Split the DataFrame into chunks
        chunks = numpy.array_split(self.record.tsv, numpy.ceil(tot / batch_size))
        for i, chunk in enumerate(chunks):
            self.process_batch(chunk, start=start, allow_duplicates=allow_duplicates, verbose=verbose, start_time=start_time, tot=tot, i=(i+1)*batch_size)
        if verbose:
            self._time(start_time, tot, i=0, final=True)

    def process_batch(self, batch, start, allow_duplicates, verbose, start_time, tot, i, final=False):
        for _, row in batch.iterrows():
            self.write_row(row, start=start, allow_duplicates=allow_duplicates)
        if verbose:
            self._time(start_time, tot, i)
        # Clear the batch to free memory
        del batch
        import gc
        gc.collect()

    def _time(self, start_time, tot, i, final=False):
        t = round(time.time() - start_time, 3)
        if not final:
            print(f"On row {i} of {tot} at {timedelta(seconds=t)}")
        else:
            print(f"*** Completed checks and buffer loading on {tot} rows after {str(timedelta(seconds=t))}")

    def write_row(self, row, start=None, allow_duplicates=False):
        return False

class NewSplitWriter(CurationWriter):

    def write_row(self, row, start=None):
        logging.debug(f"Processing row: {row}")
        
        try:
            s = [split(dbd=self.object_lookup['driver'][row['DBD']],
                       ad=self.object_lookup['driver'][row['AD']],
                       synonyms=row.get('synonyms', ''),
                       xrefs=row.get('dbxrefs', ''))]
            logging.debug(f"Split object created: {s}")
            
            self.feature_mover.gen_split_ep_feat(s, commit=False)
            logging.debug("Feature mover generated split expression pattern feature without committing.")
        
        except Exception as e:
            logging.error(f"Exception occurred while processing row: {row}, error: {e}")
            raise

    def commit(self):
        logging.debug("Committing features...")
        
        ni = self.feature_mover.ni.commit()
        ew = self.feature_mover.ew.commit()
        
        if not ew or not ni:
            logging.error("Commit failed: ew or ni returned False.")
            return False
        else:
            logging.debug("Commit successful.")
            return True


class NewMetaDataWriter(CurationWriter):

    """Wrapper object for adding new metatadata to existing entities."""

    def __init__(self, *args, **kwargs):
        super(NewMetaDataWriter, self).__init__(*args, **kwargs)
        self.rels = self.get_rels()
        logging.info(f"NewMetaDataWriter initialized for record: {self.record.cr.path}")

    def commit(self, chunk_length=1000, verbose=False):
        r = self.ew.commit(chunk_length=chunk_length, verbose=verbose)
        if False in r:
            self.stat = False
        return r

    def get_rels(self):
        rels = self.record.tsv['relation']
        unknown_rels = set(rels) - set(self.record.rel_spec.keys())
        if unknown_rels:
            self.warn(context_name='relations', context='',
                      message="Unknown relations used %s. "
                              "Please extend relations_spec.yaml "
                              "if you need new relations." % str(unknown_rels))
            self.stat = False
        return list(set(rels)-unknown_rels)

    def _generate_edge_annotations(self, r):
        """Generates edge annotation dict from pandas table row, using config as a lookup for edge annotation rows."""
        edge_annotations = {}
        for k, v in r.items():
            if not v:
                continue
            if v and (k in self.record.spec.keys()) \
                    and 'edge_annotation' in self.record.spec[k].keys() \
                    and self.record.spec[k]['edge_annotation']:
                edge_annotations[k] = v
        return edge_annotations

    def write_row(self, row, start=None, allow_duplicates=False):
        logging.debug(f"Processing row: {row}")
    
        def subject_kwarg_proc(rw):
            mapping = {'xref_db': 'subject_external_db',
                       'xref_acc': 'subject_external_id',
                       'id': 'subject_id',
                       'label': 'subject_name'}
            logging.debug(f"Subject mapped: {mapping}")
            return {k: rw[v] for k, v in mapping.items() if v in list(rw.keys())}
    
        def object_kwarg_proc(rw):
            mapping = {'xref_db': 'object_external_db',
                       'xref_acc': 'object_external_id',
                       'id': 'ind_object_id',
                       'label': 'object'}
            logging.debug(f"Object mapped: {mapping}")
            return {k: rw[v] for k, v in mapping.items() if v in list(rw.keys())}
    
        s = VfbInd(**subject_kwarg_proc(row))
        logging.debug(f"Subject: {s}")
    
        edge_annotations = self._generate_edge_annotations(row)
        logging.debug(f"Edge annotations: {edge_annotations}")
    
        r = row['relation']
        logging.debug(f"Relation: {r}")
        o_is_ind = False
    
        if ('object_external_id' in row.keys()) and ('object_external_db') in row.keys():
            ind = VfbInd(**object_kwarg_proc(row))
            logging.debug(f"Object individual: {ind}")
            object_id = self.get_ind_id(ind, 'object')
            logging.debug(f"Object ID: {object_id}")
            o_is_ind = True
        elif 'ind_object_id' in row.keys():
            object_id = row['ind_object_id']
            logging.debug(f"Object ID: {object_id}")
            o_is_ind = True
        elif 'object' in row.keys():
            o = escape_string_for_neo(row['object'])
            if not (o in self.object_lookup[r].keys()):
                self.warn(context_name="row", context=dict(row),
                          message="Not attempting to write row due to invalid object '%s'." % row['object'])
                return False
            else:
                object_id = self.object_lookup[r][o]
                logging.debug(f"Object ID: {object_id}")
        else:
            warnings.warn("Don't know how to process %s" % str(row))
            return False
    
        if r not in self.rels:
            self.warn(context_name="row", context=dict(row),
                      message="Not attempting to write row due to invalid relation '%s'." % r)
            return False
    
        if edge_annotations is None:
            edge_annotations = {}
        subject_id = self.get_ind_id(s, 'subject')
        logging.debug(f"Subject ID: {subject_id}")
    
        if subject_id and object_id:
            if r == 'is_a':
                if o_is_ind:
                    self.warn(context_name="object",
                              context=o,
                              message="You can't classify an individual with an individual")
                    self.stat = False
                else:
                    self.ew.add_named_type_ax(s=subject_id,
                                              o=object_id,
                                              edge_annotations=edge_annotations,
                                              match_on='short_form')
                    logging.debug(f"Added named type axiom: {subject_id} -> {object_id}")
                return True
            elif r in self.relation_lookup.keys():
                relation_id = self.relation_lookup[r]
                if o_is_ind:
                    self.ew.add_fact(s=subject_id,
                                     r=relation_id,
                                     o=object_id,
                                     edge_annotations=edge_annotations,
                                     match_on='short_form')
                    logging.debug(f"Added fact: {subject_id} -[{relation_id}]-> {object_id}")
                else:
                    self.ew.add_anon_type_ax(s=subject_id,
                                             r=relation_id,
                                             o=object_id,
                                             edge_annotations=edge_annotations,
                                             match_on='short_form')
                    logging.debug(f"Added anonymous type axiom: {subject_id} -[{relation_id}]-> {object_id}")
                return True
            else:
                warnings.warn("The relation name provided is not one of the list allowed for curation: %s" % str(self.relation_lookup.keys()))
                return False
        else:
            return False

    def get_ind_id(self, i: VfbInd, context):
        if i.xref_db and i.xref_acc:
            query = "MATCH (s:Site)<-[r:database_cross_reference]-(i:Individual) " \
                    "WHERE s.short_form = '%s' " \
                    "AND r.accession = ['%s']" \
                    "RETURN i.short_form as vfb_id" % (i.xref_db, i.xref_acc)
            q = self.ew.nc.commit_list([query])
            if not q:
                self.warn(context_name="%s individual" % context,
                          context=i,
                          message="VFB subject query fail")
                self.stat = False
            else:
                r = results_2_dict_list(q)
                if len(r) == 1:
                    return r[0]['vfb_id']
                elif not r:
                    self.warn(context_name='%s_individual' % context,
                              context=i,
                              message="Unknown xref: %s:%s"
                                      "" % (i.xref_db, i.xref_acc))
                    self.stat = False
                else:
                    self.warn(context_name='%s_individual' % context,
                              context=i,
                              message='Multiple matches for xref: %s:%s - %s'
                                      '' % (i.xref_db,
                                            i.xref_acc,
                                            str([x['vfb_id'] for x in r])))
                    self.stat = False
        elif i.id:
            if i.label:
                query = """MATCH (i:Individual { short_form: '%s'})
                           RETURN i.label as name""" % i.id
                q = self.ew.nc.commit_list([query])
                if not q:
                    self.warn(context_name="%s individual" % context,
                                context=i,
                                message="VFB %s query fail" % context)
                    self.stat = False
                else:
                    r = results_2_dict_list(q)
                    if len(r) == 1:
                        name = r[0]['name']
                    elif not r:
                        self.warn(context_name='%s_individual' % context,
                                  context=i,
                                  message="Unknown individual: %s"
                                          "" % i.id)
                        self.stat = False
                        return False
                    if name == i.label:
                        return i.id
                    else:
                        self.warn(context_name="%s individual" % context,
                                  context=i,
                                  message="You provided label: (%s) and ID: (%s), " \
                                          "but in the KB this IS matches %s " \
                                          "" % (i.label, i.id, r[0]['name']))
                        self.stat = False
            else:
                self.warn(context_name="%s individual" % context,
                          context=i,
                          message="No name provided, so adding relationship to individual without name/ID crosscheck")
                return i.id

class NewImageWriter(CurationWriter):

    def __init__(self, *args, **kwargs):
        super(NewImageWriter, self).__init__(*args, **kwargs)
        self.set_flybase_lookups()
        logging.info(f"NewImageWriter initialized for record: {self.record.cr.path}")

    def set_flybase_lookups(self):
        fb_feat_columns = [k for k, v in self.record.spec.items()
                                   if 'flybase_feature' in v.keys()
                                   and v['flybase_feature']
                                   and k in self.record.tsv.columns]

        for c in fb_feat_columns:
            features = set(self.record.tsv[c].dropna())
            self.extend_lookup_from_flybase(features, key=c)

    def gen_pw_args(self, row, start):
        stat = True

        row.fillna('', inplace=True)
        out = {}
        out['start'] = start
        for k, v in self.record.spec.items():
            if ('pattern_arg' in v.keys()) and ('pattern_dict_key' in v.keys()):
                out[v['pattern_arg']] = {}

        out['anon_anatomical_types'] = []

        if 'anat_id' in row and row['anat_id'] in self.object_lookup.get('anat_id', {}):
            out['anat_id'] = self.object_lookup['anat_id'][row['anat_id']]

        if self.record.type == 'split':
            if row['DBD'] in self.object_lookup['DBD'].keys():
                dbd_id = self.object_lookup['DBD'][row['DBD']]
            else:
                self.warn(context_name="row", context=dict(row),
                          message="Not attempting to write row due to"
                                  " invalid object '%s'." % row['DBD'])
                stat = False
            if row['AD'] in self.object_lookup['AD'].keys():
                ad_id = self.object_lookup['AD'][row['AD']]
            else:
                self.warn(context_name="row", context=dict(row),
                          message="Not attempting to write row due to"
                                  " invalid object '%s'." % row['AD'])
                stat = False
            if not stat:
                return False
            else:
                out['anatomical_type'] = 'VFBexp_' + dbd_id + ad_id

        elif self.record.type == 'ep':
            if row['driver'] in self.object_lookup['driver'].keys():
                driver_id = self.object_lookup['driver'][row['driver']]
                self.feature_mover.generate_expression_patterns(driver_id)
                out['anatomical_type'] = 'VFBexp_' + driver_id
            else:
                self.warn(context_name="row", context=dict(row),
                          message="Not attempting to write row due to"
                                  " invalid object '%s'." % row['driver'])
                return False

        for k, v in self.record.spec.items():
            if not row[k]:
                continue
            if 'multiple' in v.keys() and v['multiple']:
                value = row[k].split('|')
                multiple = True
            else:
                value = [row[k]]
                multiple = False

            if 'restriction' in v.keys():
                obj = []
                for o in value:
                    if o in self.object_lookup[k].keys():
                        obj.append(self.object_lookup[k][o])
                    else:
                        self.warn(context_name="row", context=dict(row),
                                  message="Not attempting to write row due to"
                                          " invalid object '%s'." % o)
                        stat = False
                if not obj:
                    continue
                else:
                    value = obj
                if k in self.record.rel_spec.keys():
                    if k == 'is_a':
                        out['anatomical_type'] = value[0]
                    else:
                        for val in value:
                            out['anon_anatomical_types'].append((self.relation_lookup[k],
                                                                 val))
            if 'pattern_arg' in v.keys():
                if 'pattern_dict_key' in v.keys():
                    out[v['pattern_arg']][v['pattern_dict_key']] = value
                else:
                    if multiple:
                        out[v['pattern_arg']] = value
                    else:
                        out[v['pattern_arg']] = value[0]
        if stat:
            return out
        else:
            self.stat = False
            return False

    def write_row(self, row, start='100000', allow_duplicates=False):
        kwargs = self.gen_pw_args(row, start=start)
        if kwargs:
            logging.debug(f"Writing row with arguments: {kwargs}")
            self.pattern_writer.add_anatomy_image_set(**kwargs, hard_fail=not allow_duplicates, allow_duplicates=allow_duplicates)

    def commit(self, ew_chunk_length=1500, ni_chunk_length=1500, verbose=False):
        if verbose:
            logging.info(f"Committing changes with ew_chunk_length={ew_chunk_length} and ni_chunk_length={ni_chunk_length}")
        if not self.pattern_writer.commit(ew_chunk_length=ew_chunk_length, ni_chunk_length=ni_chunk_length, verbose=verbose):
            self.stat = False


        # Strategies for rdfs:label matching

        # 1. use match_on = label - some risk of choosing term from wrong ontology. This could potentially be managed in KB
        # via enforced label uniquenes.  This would require some clean up! We already have 7 pairs of :Class nodes with
        # matching labels, although none are currently used in annotation.  3 are GO:FBbt CC term, the rest are FBbi or
        # SO terms with duplicate names. The only term likely to cause problems is GO:Cell. It is not clear to me why GO
        # is in the KB at all. It is not used in annotation.
        # BUT: enforcing uniquenes is a pain given that we will potentially load many external ontologies, some of which
        # already have duplicates!

        # 2. match_on = label + some additional match criteria (label, or short_form regex). This would require some
        # re-engineering of core methods. The easiest strategy to support would be filter on neo4j:label.  However, the
        # KB is deliberately poor in labels - maintaining them would be an overhead. (extending core methods to support
        # labels seems like a good idea anyway - potentially useful for pdb).

        # 3. Roll lookup(s) that enforce some set of restrictions - e.g. short_form or iri regex.  Use lookup (dict) to
        # run add_anatomy_image set using short_forms.  We can use these lookups to enforce some annotation consistency
        # The maintenance overhead here is on the load table method and is relatively easy to manage through kwargs.
        # is_a: broad - maybe just maintain a blacklist
        # part_of: FBbt only
        # expresses: iri filter for FlyBase?
        # kwargs be on KB_pattern_writer __init__ so lookups only need to be rolled once.
