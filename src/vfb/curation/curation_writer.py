from uk.ac.ebi.vfb.neo4j.neo4j_tools import results_2_dict_list
from dataclasses import dataclass
from typing import List
from uk.ac.ebi.vfb.neo4j.KB_tools import kb_owl_edge_writer, KB_pattern_writer
from uk.ac.ebi.vfb.neo4j.flybase2neo.feature_tools import FeatureMover
from uk.ac.ebi.vfb.neo4j.flybase2neo.pub_tools import pubMover
from .peevish import Record
import numpy
import warnings


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
            warnings.warn('Not enough information supplied to identify subject. Minimaun =  dbxref or ID, you supplied only %s' % self.__str__())

            self._stat = False

# Not sure this class still needed.
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

    def __init__(self, endpoint, usr, pwd, record: Record):
        """KB connection: endpoint, usr, pwd
        lookup_config: a dict of lists of LookupConf keyed on column name or relation name.
        relation_lookup: name: short_form dictionary for valid relations"
        """

        # TBD: how to deal with FB features.  Maybe needs to be outside of this by adding to
        # KB first?
        self.pattern_writer = KB_pattern_writer(endpoint, usr, pwd)  # maybe limit this to NewImageWriter
        self.feature_mover = FeatureMover(endpoint, usr, pwd)
        self.pub_mover = pubMover(endpoint, usr, pwd)
        self.ew = self.feature_mover.ew
        self.record = record
        self.object_lookup = self.generate_object_lookups()
        self.relation_lookup = self.generate_relation_lookup()
        self.stat = True


    def commit(self):
        r = self.ew.commit()
        if not r:
            self.stat = False
        return r

    def generate_object_lookups(self):
        cl = self._generate_lookups(self._gen_lookup_config_by_header())
        rl = self._generate_lookups(self._gen_lookup_config_by_rel())
        cl['rel_object'] = rl  # Might be better to have these as separate lookups?
        return cl


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
                for k, v in self.record.rel_spec.items()
                if 'restriction' in v.keys()}

    def generate_relation_lookup(self):
        return {k: v['short_form']
                for k, v in self.record.rel_spec.items()
                if not (k == 'is_a')}  # Not keen on hard wiring here, but maybe unavoidable

    def _generate_lookups(self, conf):

        """Generate  :Class name:ID lookups from DB for loading by label.
         Lookups are defined by standard config that specifies a config:
         name:field:regex, e.g. {'part_of': {'short_form': 'FBbt_.+'}}
         name should match the kwarg for which it is to be used.
         """
        # This is just rolling a relation lookup...

        lookup_config = conf

        lookup = {}
        if lookup_config:
            # Add some type checking here?
            for name, lcs in lookup_config.items():
                lookup[name] = {}
                for c in lcs:
                    q = "MATCH (c%s) where c.%s =~ '%s' RETURN c.label as label" \
                        ", c.short_form as short_form" % (c.neo_label_string, c.field, c.regex)
                    print(q)
                    rr = self.ew.nc.commit_list([q])
                    r = results_2_dict_list(rr)
                    lookup[name].update({x['label']: x['short_form'] for x in r})
        return lookup


    def extend_lookup_from_flybase(self, features, key='expresses'):

        fu = "['"+"', ".join(features) + "']"
        ## Notes - use uniq'd IDs from features columns for lookup.
        query = "SELECT f.uniquename AS short_form, f.name AS label" \
                " FROM feature WHERE f.name IN %s" % fu
        dc = self.feature_mover.query_fb(query)  # What does this return on fail
        self.lookups[key] = {d['label']: d['short_form'] for d in dc}


class NewMetaDataWriter(CurationWriter):

    """Wrapper object for adding new metatadata to existing entities.
    Takes """

    def __init__(self, *args, **kwargs):
        super(NewMetaDataWriter, self).__init__(*args, **kwargs)
        self.rels = self.get_rels()  # May not need attribute

    def get_rels(self):
        rels = self.record.tsv['relation']
        unknown_rels = set(rels) - set(self.record.rel_spec.keys())
        if unknown_rels:
            warnings.warn("Unknown relations used %s. "
                          "Please extend relations_spec.yaml if you need new relations." % str(unknown_rels))
            self.stat = False
            return False
        else:
            return rels

    def write_rows(self):
        def kwarg_proc(r):
            mapping = {'xref_db': 'subject_external_db',
                       'xref_acc': 'subject_external_id',
                       'id': 'subject_id',
                       'label': 'subject_name'}
            return {k: r[v] for k, v in mapping.items() if v in list(r.keys())}

        for i, r in self.record.tsv.iterrows():
            # Assumes all empty cells in DataFrame replaced with empty string.
            s = VfbInd(**kwarg_proc(r))
            edge_annotations = self._generate_edge_annotations(r)
            # TODO: Refactor this to work from config
            self.write_row(s, r['relation'], r['object'], edge_annotations=edge_annotations)

    def _generate_edge_annotations(self, r):
        """Generates edge annotation dict from pandas table row, using config as a lookup for edge annotation rows."""
        # TODO - add lookup instead of relying on column header names matching AP names!
        edge_annotations = {}
        for k, v in r.items():
            if v and (k in self.record.spec.keys()) \
                    and 'edge_annotation' in self.record.spec[k].keys() \
                    and self.record.spec[k]['edge_annotation']:
                edge_annotations[k] = v
        return edge_annotations


    def write_row(self,
                  s: VfbInd,
                  r: str, o: str,
                  edge_annotations=None):
        """s = subject individual. Type: VFB_ind
           r = relation label
           o = object label
           edge_annotations: Optionally annotate edge"""
        if edge_annotations is None:
            edge_annotations = {}
        subject_id = self.get_subject_id(s)
        object_id = self.object_lookup['rel_object'][r][o]
        if subject_id and object_id:
            if r == 'is_a':
                self.ew.add_named_type_ax(s=subject_id,
                                          o=object_id,
                                          edge_annotations=edge_annotations,
                                          match_on='short_form')
                return True
            elif r in self.relation_lookup.keys():
                relation_id = self.relation_lookup[r]
                self.ew.add_anon_type_ax(s=subject_id,
                                         r=relation_id,
                                         o=object_id,
                                         edge_annotations=edge_annotations,
                                         match_on='short_form')
                return True
            else:
                warnings.warn("The relation name provided is not one of "
                              "the list allowed for curation: %s"
                              "" % str(self.lookups['relations'].keys()))
                return False
        else:
            return False

    def get_subject_id(self, s: VfbInd):
        if s.xref_db and s.xref_acc:
            # query to find id
            query = "MATCH (s:Site)<-[r:hasDbXref]-(i:Individual) " \
                    "WHERE s.short_form = '%s' " \
                    "ANd r.accession = '%s'" \
                    "RETURN i.short_form as subject_id" % (s.xref_db, s.xref_acc)
            q = self.ew.nc.commit_list([query])
            if not q:
                warnings.warn("VFB subject query fail") # Better make exception ?
                self.stat = False  # Better try except here?
            else:
                r = results_2_dict_list(q)
                if len(r) == 1:
                    return r[0]['subject_id']
                elif not r:
                    warnings.warn("Unknown xref: %s:%s" % (s.xref_db, s.xref_acc))
                    self.stat = False
                else:
                    warnings.warn('Multiple matches for xref: %s:%s - %s' % (s.xref_db,
                                                                             s.xref_acc,
                                                                             str([x['subject_id'] for x in r])))
                    self.stat = False

        elif s.label:
            if s.label in self.lookups['subject']:
                id = self.lookups['subject'][s.label]
                if id == s.id:
                    return s.id
                else:
                    warnings.warn("You provided label: (%s) and ID: (%s), "
                                  "but in the KB this label matches %s"
                                  "" % (s.label, s.id, id))
                    return False
            else:
                warnings.warn("Unknown label (%s) provided id (%s)"
                              "" % (s.label, s.id))
        else:
            # Allows for bare IDs. But should we?
            return s.id

class NewImageWriter(CurationWriter):

    def __init__(self, *args, **kwargs):
        super(NewImageWriter, self).__init__(*args, **kwargs)
        # some extensions here

    def load_new_image_table(self,
                             dataset,
                             imaging_type,
                             label,
                             start,
                             template,
                             anatomical_type,
                             classification_reference='',
                             classification_comment='',
                             part_of='',
                             expresses='',
                             index=False,
                             center=(),
                             anatomy_attributes=None,
                             dbxrefs=None,
                             dbxref_strings=None,
                             image_filename='',
                             match_on='short_form',
                             orcid='',
                             name_id_sub_via_lookup=False,
                             hard_fail=False):

        """Method for loading new image curation tables.
        Spec: https://github.com/VirtualFlyBrain/curation/blob/test_curation/records/new_images/anatomy_spec.yaml
        All ontology fields use labels"""

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

        args = locals()
        for k, v in args.items():
            if k in self.lookups.keys():
                args[k] = self.lookups[k][v]
        self.pattern_writer.add_anatomy_image_set(**args)  # Surely possible to do this on the original method!
