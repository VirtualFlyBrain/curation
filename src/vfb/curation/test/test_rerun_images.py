import unittest
from types import SimpleNamespace
from unittest import mock
import pandas as pd
from ..curation_writer import NewImageWriter


def writer(kb_rows, dataset='DS1'):
    """A NewImageWriter with a record of anat_ids A-D and a KB returning kb_rows ([id, [DataSets]])."""
    w = object.__new__(NewImageWriter)
    w.record = SimpleNamespace(tsv=pd.DataFrame({'anat_id': ['A', 'B', 'C', 'D']}), y={'DataSet': dataset},
                               cr=SimpleNamespace(name='rec', path='rec.tsv'))
    w.failures, w.stat = [], True
    nc = mock.Mock()
    nc.commit_list.return_value = [{'data': [{'row': r} for r in kb_rows]}]
    w.pattern_writer = SimpleNamespace(ni=SimpleNamespace(nc=nc))
    return w


KB = [['A', ['DS1', 'Dataset one']], ['B', []], ['C', ['DS2']]]   # D not in the KB


class TestFindAlreadyLoaded(unittest.TestCase):

    def test_default_skips_own_dataset_and_rejects_others(self):
        w = writer(KB)
        w.find_already_loaded()
        self.assertEqual({'A'}, w.already_loaded)
        self.assertEqual(set(), w.rewritten)
        self.assertEqual(['B', 'C'], [f['context'] for f in w.failures])
        self.assertFalse(w.stat)

    def test_allow_duplicates_rewrites_partial_rows(self):
        w = writer(KB)
        w.find_already_loaded(allow_duplicates=True)
        self.assertEqual(set(), w.already_loaded)
        self.assertEqual({'A', 'B'}, w.rewritten)
        self.assertEqual(['C'], [f['context'] for f in w.failures])   # another DataSet's id: still an error

    def test_allow_duplicates_clean(self):
        w = writer([['A', ['DS1']], ['B', []]])
        w.find_already_loaded(allow_duplicates=True)
        self.assertEqual([], w.failures)
        self.assertTrue(w.stat)


if __name__ == '__main__':
    unittest.main()
