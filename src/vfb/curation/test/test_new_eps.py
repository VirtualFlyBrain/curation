import os
import tempfile
import unittest
from collections import namedtuple
from unittest import mock

import pandas as pd

from ..curation_writer import CurationWriter, NewEpWriter
from ..peevish import Record, process_file_path

Feat = namedtuple('Feat', ['label'])
FEATS = {'FBtp0000001': Feat('P{NPFR-GAL4.T}'), 'FBti0000002': Feat('P{GawB}fru[NP21]')}


def writer(rows, existing=(), labels=(), name_lookup=None):
    """A NewEpWriter on a fake record and KB: existing = [short_form], labels = [(label, sf)]."""
    w = object.__new__(NewEpWriter)
    w.record = mock.Mock()
    w.record.tsv = pd.DataFrame(rows).astype(object)
    w.record.cr.name = w.record.cr.path = 'ep_test_261112'
    w.failures, w.stat, w.classes = [], True, {}
    w.object_lookup = {'driver': name_lookup or {}}
    w.feature_mover = mock.Mock()
    w.feature_mover.name_synonym_lookup.side_effect = lambda ids: {i: FEATS[i] for i in ids if i in FEATS}
    w.ew = w.feature_mover.ew

    def query(statement, **params):
        if 'c.short_form IN $sfs' in statement:
            return [{'sf': sf} for sf in existing if sf in params['sfs']]
        if 'c.label IN $labels' in statement:
            return [{'label': l, 'sf': sf} for l, sf in labels if l in params['labels']]
        raise AssertionError(statement)
    w.query = query
    return w


SF = 'VFBexp_FBtp0000001'


class TestNewEpWriter(unittest.TestCase):

    def test_class_per_driver(self):
        w = writer([{'driver_id': 'FBtp0000001', 'comment': 'Sapiro 2019 NPFR samples'},
                    {'driver_id': 'FBti0000002'}])
        self.assertTrue(w.write_rows())
        self.assertEqual(list(w.classes), [SF, 'VFBexp_FBti0000002'])
        self.assertEqual(w.classes[SF]['label'], 'P{NPFR-GAL4.T} expression pattern')
        self.assertEqual(w.classes['VFBexp_FBti0000002']['label'], 'P{GawB}fru[NP21] expression pattern')

    def test_names_resolved_and_must_agree_with_ids(self):
        names = {'P{NPFR-GAL4.T}': 'FBtp0000001', 'NPFR[GAL4.T]': 'FBal0000003'}
        w = writer([{'driver': 'P{NPFR-GAL4.T}'}], name_lookup=names)
        self.assertTrue(w.write_rows())
        self.assertEqual(list(w.classes), [SF])
        w = writer([{'driver': 'P{NPFR-GAL4.T}', 'driver_id': 'FBti0000002'}], name_lookup=names)
        self.assertFalse(w.write_rows())
        self.assertIn('not FBti0000002', w.failures[0]['message'])
        # a name that resolves to an allele, not a driver
        w = writer([{'driver': 'NPFR[GAL4.T]'}], name_lookup=names)
        self.assertFalse(w.write_rows())
        self.assertIn('FBal0000003', w.failures[0]['message'])

    def test_bad_or_unknown_driver_fails_the_record(self):
        w = writer([{'driver_id': 'FBal0000003'}, {'driver_id': 'FBtp0000001'}])
        self.assertFalse(w.write_rows())
        self.assertIn('FBtp/FBti', w.failures[0]['message'])
        w = writer([{'driver': 'P{nope}'}])
        self.assertFalse(w.write_rows())
        w = writer([{'driver_id': 'FBtp0000009'}])
        self.assertFalse(w.write_rows())
        self.assertIn('Not in FlyBase: FBtp0000009', w.failures[0]['message'])

    def test_existing_class_is_fine(self):
        w = writer([{'driver_id': 'FBtp0000001'}], existing=[SF],
                   labels=[('P{NPFR-GAL4.T} expression pattern', SF)])
        self.assertTrue(w.write_rows())
        self.assertTrue(w.classes[SF]['existing'])

    def test_label_used_by_another_class_fails(self):
        w = writer([{'driver_id': 'FBtp0000001'}], labels=[('P{NPFR-GAL4.T} expression pattern', 'VFBexp_other')])
        self.assertFalse(w.write_rows())
        self.assertIn('VFBexp_other', w.failures[0]['message'])

    def test_commit_uses_the_expression_import_code(self):
        w = writer([{'driver_id': 'FBtp0000001'}, {'driver_id': 'FBti0000002'}])
        self.assertTrue(w.write_rows())
        w.batch_size = 1
        w.verify = mock.Mock(return_value=[])
        self.assertTrue(w.commit())
        self.assertEqual([c.args[0] for c in w.feature_mover.generate_expression_patterns.call_args_list],
                         [['FBtp0000001'], ['FBti0000002']])
        self.assertEqual(w.feature_mover.generate_expression_patterns.call_args.kwargs, {'commit': False})
        w = writer([{'driver_id': 'FBtp0000001'}, {'driver_id': 'FBti0000002'}])
        w.write_rows()
        w.batch_size = 1
        w.verify = mock.Mock(return_value=[(SF, 'not a subclass of expression pattern')])
        self.assertFalse(w.commit())
        self.assertEqual(w.feature_mover.generate_expression_patterns.call_count, 1)
        self.assertFalse(w.stat)


class TestNewEpsRecord(unittest.TestCase):
    """A new_eps record built from the repo's spec files (run from the repo root, like test_peevish)."""

    def test_record_from_repo_spec(self):
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(d + '/new_eps/to_submit')
            path = d + '/new_eps/to_submit/ep_test_261112.tsv'
            pd.DataFrame([{'driver_id': 'FBtp0000001', 'driver': 'P{NPFR-GAL4.T}', 'comment': 'test'}]
                         ).to_csv(path, sep='\t', index=False)
            rec = Record(spec_path='records/new_eps', cur_recs=(process_file_path(path),))
        self.assertTrue(rec.stat)
        self.assertEqual(rec.gross_type, 'new_eps')
        self.assertEqual(rec.rel_spec, {})  # relations_spec.yaml is comment-only
        w = object.__new__(CurationWriter)
        w.record = rec
        self.assertEqual(w.generate_relation_lookup(), {})


if __name__ == '__main__':
    unittest.main()
