from uk.ac.ebi.vfb.neo4j.neo4j_tools import results_2_dict_list
from dataclasses import dataclass
from typing import List
from uk.ac.ebi.vfb.neo4j.KB_tools import kb_owl_edge_writer, KB_pattern_writer
import warnings




@dataclass
class VfbInd:
    label: str = ''
    id: str = ''
    xref: str = ''

    def __post_init__(self):
        self.validate()

    def validate(self):
        """Must have either label + id OR xref
          xref must contain a single colon"""
        stat = True
        if self.xref:
            if not(len(self.xref.split(':')) == 2):
                Exception("%s doesn't look like "
                              "a single xref, expected db:acc" % self.xref)
            if self.id:
                Exception("ID and xref provided (%s + %s) "
                              "Which do you want me to use?"
                              "" % (self.id, self.xref))
                stat = False
        if self.id and not self.xref:
            if not self.label:
                Exception("ID provided (%s) but no label. "
                              "Please provide a label "
                              "(name) to go with this ID for cross-checking"
                              "" % self.id)
                stat = False
        return stat


@dataclass # post init step addition of attribute prevents adding frozen=True
class LConf:
    """field = node attribute  to which regex restriction"""
    field: str
    labels: List[str]
    regex: str

    def __post_init__(self):
        if self.labels:
            self.neo_label_string = ':' + ':'.join(self.labels)
        else:
            self.neo_label_string = ''


class CurationWriter:
    """A wrapper class for loading annotation curation tables to VFB KB"""

    def __init__(self, endpoint, usr, pwd,
                 lookup_config: dict, relation_lookup: dict):
        """KB connection: endpoint, usr, pwd
        lookup_config: a dict of lists of LookupConf keyed on column name or relation name.
        relation_lookup: name: short_form dictionary for valid relations"
        """

        # TBD: how to deal with FB features.  Maybe needs to be outside of this by adding to
        # KB first?
        self.pattern_writer = KB_pattern_writer(endpoint, usr, pwd)
        self.ew = self.pattern_writer.ew
        self.lookups = self.generate_lookups(lookup_config)
        self.lookups['relations'] = relation_lookup

    def commit(self):
        return self.ew.commit()


    def generate_lookups(self, lookup_config):
        # Maybe make this private & have it directly modify self.lookups?
        """Generate  :Class name:ID lookups from DB for loading by label.
         Lookups are defined by standard config that specifies a config:
         name:field:regex, e.g. {'part_of': {'short_form': 'FBbt_.+'}}
         name should match the kwarg for which it is to be used.
         """
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
        else:
            return {}

    def add_assertion_to_VFB_ind(self, s: VfbInd,
                                 r: str, o: str,
                                 edge_annotations=None):
        """s = subject individual. Type: VFB_ind
           r = relation label
           o = object label
           edge_annotations: Optionally annotate edge"""
        if edge_annotations is None:
            edge_annotations = {}
        subject_id = self.get_subject_id(s)
        object_id = self.lookups[r][o]
        if subject_id and object_id:
            if r == 'is_a':
                self.ew.add_named_type_ax(s=subject_id,
                                          o=object_id,
                                          edge_annotations=edge_annotations,
                                          match_on='short_form')
                return True
            elif r in self.lookups['relations'].keys():
                relation_id = self.lookups['relations'][r]
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
        if s.xref:
            # query to find id
            xrefl = s.xref.split(':')
            db = xrefl[0]
            acc = xrefl[1]
            query = "MATCH (s:Site)<-[r:hasDbXref]-(i:Individual) " \
                    "WHERE s.short_form = '%s' " \
                    "ANd r.accession = '%s'" \
                    "RETURN i.short_form as subject_id" % (db, acc)
            q = self.ew.nc.commit_list([query])
            if not q:
                return False  # Better try except here?
            else:
                r = results_2_dict_list(q)
                if len(r) == 1:
                    return r[0]['subject_id']
                else:
                    warnings.warn()
                    return False

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


    def load_new_image_table(self,
                              dataset,
                              imaging_type,
                              label,
                              start,
                              template,
                              anatomical_type,
                              classification_reference='',
                              classification_comment='',
                              part_of = '',
                              expresses = '',
                              index=False,
                              center=(),
                              anatomy_attributes=None,
                              dbxrefs=None,
                              dbxref_strings=None,
                              image_filename='',
                              match_on='short_form',
                              orcid='',
                              name_id_sub_via_lookup = False,
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