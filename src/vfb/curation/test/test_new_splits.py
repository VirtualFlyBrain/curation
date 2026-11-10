import unittest
from collections import namedtuple
from unittest import mock

import pandas as pd

from ..curation_writer import NewSplitWriter

Feat = namedtuple('Feat', ['label'])
FEATS = {'FBtp0000001': Feat('P{R1-p65.AD}'), 'FBtp0000002': Feat('P{R2-GAL4.DBD}'),
         'FBtp0000003': Feat('P{R3-p65.AD}')}


def writer(rows, existing=(), labels=(), name_lookup=None):
    """A NewSplitWriter on a fake record and KB: existing = [(short_form, synonyms)], labels = [(label, sf)]."""
    w = object.__new__(NewSplitWriter)
    w.record = mock.Mock()
    w.record.tsv = pd.DataFrame(rows).astype(object)
    w.record.cr.name = w.record.cr.path = 'split_test_261110'
    w.failures, w.stat, w.classes = [], True, {}
    w.object_lookup = {'AD': {}, 'DBD': {}}
    w.object_lookup.update(name_lookup or {})
    w.feature_mover = mock.Mock()
    w.feature_mover.name_synonym_lookup.side_effect = lambda ids: {i: FEATS[i] for i in ids if i in FEATS}

    def query(statement, **params):
        if 'c.short_form IN $sfs' in statement:
            return [{'sf': sf, 'synonyms': s} for sf, s in existing if sf in params['sfs']]
        if 'c.label IN $labels' in statement:
            return [{'label': l, 'sf': sf} for l, sf in labels if l in params['labels']]
        raise AssertionError(statement)
    w.query = query
    return w


SF = 'VFBexp_FBtp0000002FBtp0000001'


class TestNewSplitWriter(unittest.TestCase):

    def test_lines_sharing_a_pair_are_one_class(self):
        w = writer([{'AD_id': 'FBtp0000001', 'DBD_id': 'FBtp0000002', 'synonyms': 'SS1|JRC_SS1',
                     'dbxrefs': 'FlyLightSplit:SS1'},
                    {'AD_id': 'FBtp0000001', 'DBD_id': 'FBtp0000002', 'synonyms': 'IS9',
                     'dbxrefs': 'FlyLightRaw:IS9|FlyLightSplit:SS1'}])
        self.assertTrue(w.write_rows())
        self.assertEqual(list(w.classes), [SF])
        c = w.classes[SF]
        self.assertEqual(c['synonyms'], ['SS1', 'JRC_SS1', 'IS9'])
        self.assertEqual(c['xrefs'], ['FlyLightSplit:SS1', 'FlyLightRaw:IS9'])
        self.assertEqual(c['label'], 'P{R2-GAL4.DBD} ∩ P{R1-p65.AD} expression pattern')

    def test_names_resolved_and_must_agree_with_ids(self):
        names = {'AD': {'P{R1-p65.AD}': 'FBtp0000001'}, 'DBD': {'P{R2-GAL4.DBD}': 'FBtp0000002'}}
        w = writer([{'AD': 'P{R1-p65.AD}', 'DBD': 'P{R2-GAL4.DBD}', 'synonyms': 'SS1'}], name_lookup=names)
        self.assertTrue(w.write_rows())
        self.assertEqual(list(w.classes), [SF])
        w = writer([{'AD': 'P{R1-p65.AD}', 'AD_id': 'FBtp0000003', 'DBD_id': 'FBtp0000002'}], name_lookup=names)
        self.assertFalse(w.write_rows())
        self.assertIn('not FBtp0000003', w.failures[0]['message'])

    def test_unknown_hemidriver_fails_the_record(self):
        w = writer([{'AD': 'P{nope}', 'DBD_id': 'FBtp0000002'},
                    {'AD_id': 'FBtp0000001', 'DBD_id': 'FBtp0000002'}])
        self.assertFalse(w.write_rows())
        w = writer([{'AD_id': 'FBtp0000009', 'DBD_id': 'FBtp0000002'}])
        self.assertFalse(w.write_rows())
        self.assertIn('Not in FlyBase: FBtp0000009', w.failures[0]['message'])

    def test_existing_class_keeps_its_synonyms(self):
        w = writer([{'AD_id': 'FBtp0000001', 'DBD_id': 'FBtp0000002', 'synonyms': 'IS9|SS1'}],
                   existing=[(SF, ['SS1', 'old'])],
                   labels=[('P{R2-GAL4.DBD} ∩ P{R1-p65.AD} expression pattern', SF)])
        self.assertTrue(w.write_rows())
        self.assertEqual(w.classes[SF]['synonyms'], ['SS1', 'old', 'IS9'])

    def test_label_used_by_another_class_fails(self):
        w = writer([{'AD_id': 'FBtp0000001', 'DBD_id': 'FBtp0000002'}],
                   labels=[('P{R2-GAL4.DBD} ∩ P{R1-p65.AD} expression pattern', 'VFBexp_other')])
        self.assertFalse(w.write_rows())
        self.assertIn('VFBexp_other', w.failures[0]['message'])

    def test_commit_batches_and_stops_on_failed_read_back(self):
        rows = [{'AD_id': 'FBtp0000001', 'DBD_id': 'FBtp0000002'},
                {'AD_id': 'FBtp0000003', 'DBD_id': 'FBtp0000002'}]
        w = writer(rows)
        self.assertTrue(w.write_rows())
        w.batch_size = 1
        w.verify = mock.Mock(return_value=[])
        self.assertTrue(w.commit())
        self.assertEqual(w.feature_mover.gen_split_ep_feat.call_count, 2)
        self.assertEqual(w.feature_mover.ni.commit.call_args.kwargs, {'chunk_length': 200})
        w = writer(rows)
        w.write_rows()
        w.batch_size = 1
        w.verify = mock.Mock(return_value=[(SF, '1 of 2 hemidrivers')])
        self.assertFalse(w.commit())
        self.assertEqual(w.feature_mover.gen_split_ep_feat.call_count, 1)
        self.assertFalse(w.stat)


if __name__ == '__main__':
    unittest.main()
