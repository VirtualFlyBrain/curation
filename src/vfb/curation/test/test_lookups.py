import unittest
from types import SimpleNamespace
import pandas as pd
import json
from unittest import mock
import requests
from ..curation_writer import record_label_candidates, label_chunks, CurationWriter


class TestRecordLabelCandidates(unittest.TestCase):

    def test_tsv_and_yaml_values(self):
        rec = SimpleNamespace(
            tsv=pd.DataFrame({'object': ['adult neuron', 'T4 neuron|T5 neuron', None],
                              'relation': ['is_a', 'is_a', 'part_of']}),
            y={'DataSet': 'Berg2025a', 'Imaging_type': ['SB-SEM'], 'Start': 100})
        c = record_label_candidates(rec)
        for v in ('adult neuron', 'T4 neuron', 'T5 neuron', 'is_a', 'part_of', 'Berg2025a', 'SB-SEM'):
            self.assertIn(v, c)

    def test_escaped_values_also_unescaped(self):
        # lookup keys are escape_string(label): a value given escaped must still find the KB label
        rec = SimpleNamespace(tsv=pd.DataFrame({'DBD': ['Scer\\\\GAL4[DBD.R42F06]'],
                                                'AD': ['say \\"hi\\"']}), y=False)
        c = record_label_candidates(rec)
        self.assertIn('Scer\\GAL4[DBD.R42F06]', c)
        self.assertIn('say "hi"', c)

    def test_padded_multiple_values(self):
        rec = SimpleNamespace(tsv=pd.DataFrame({'part_of': ['medulla | lobula']}), y=None)
        c = record_label_candidates(rec)
        self.assertIn('lobula', c)
        self.assertIn('medulla', c)


class TestLabelChunks(unittest.TestCase):

    def test_chunks_cover_all_labels_in_order_within_limit(self):
        labels = ['label %05d' % i for i in range(5000)]
        chunks = list(label_chunks(labels, 10_000))
        self.assertGreater(len(chunks), 1)
        self.assertEqual([x for c in chunks for x in c], labels)
        for c in chunks:
            self.assertLessEqual(len(json.dumps(c)), 10_000 + 2)

    def test_oversized_label_gets_its_own_chunk(self):
        self.assertEqual(list(label_chunks(['a' * 50, 'b'], 10)), [['a' * 50], ['b']])

    def test_empty(self):
        self.assertEqual(list(label_chunks([], 10)), [])


class TestGenerateLookupsChunked(unittest.TestCase):
    """_generate_lookups without a KB: a fake commit_list answers from a label table."""

    def writer(self, labels, kb, fail_first=0):
        w = CurationWriter.__new__(CurationWriter)
        w.record = SimpleNamespace(tsv=pd.DataFrame({'part_of': labels}), y=None)
        w.lookup_chunk_bytes = 200
        calls = []

        def commit_list(batch):
            calls.append(batch)
            if len(calls) <= fail_first:
                raise requests.exceptions.ChunkedEncodingError('Connection broken: IncompleteRead')
            out = []
            for s in batch:
                name = s['statement'].split("RETURN '")[1].split("'")[0]
                rows = [{'row': [name, l, kb[l]]} for l in s['parameters']['labels'] if l in kb]
                out.append({'columns': ['lookup_name', 'label', 'short_form'], 'data': rows})
            return out

        w.ew = SimpleNamespace(nc=SimpleNamespace(commit_list=commit_list))
        return w, calls

    def conf(self):
        lc = SimpleNamespace(neo_label_string=':Class', field='short_form', regex='FBbt_.+')
        return {'part_of': [lc], 'is_a': [lc]}

    def test_all_labels_found_across_chunks(self):
        labels = ['neuron %03d' % i for i in range(100)]
        kb = {l: 'FBbt_%08d' % i for i, l in enumerate(labels) if i % 3 == 0}
        w, calls = self.writer(labels, kb)
        lookup = w._generate_lookups(self.conf())
        self.assertGreater(len(calls), 1)                    # chunked
        for batch in calls:
            self.assertEqual(len(batch), 1)                  # one statement per request
        self.assertEqual(len(calls) % 2, 0)                  # both lookups for every chunk
        self.assertEqual(lookup['part_of'], kb)
        self.assertEqual(lookup['is_a'], kb)

    @mock.patch('time.sleep')
    def test_dropped_connection_retried(self, _sleep):
        w, calls = self.writer(['medulla'], {'medulla': 'FBbt_00003748'}, fail_first=1)
        self.assertEqual(w._generate_lookups(self.conf())['part_of'], {'medulla': 'FBbt_00003748'})
        self.assertEqual(len(calls), 3)                      # dropped + retried, then the second lookup

    @mock.patch('time.sleep')
    def test_gives_up_after_retries(self, _sleep):
        w, calls = self.writer(['medulla'], {}, fail_first=99)
        with self.assertRaises(requests.exceptions.ChunkedEncodingError):
            w._generate_lookups(self.conf())
        self.assertEqual(len(calls), 3)

    def test_failed_query_raises(self):
        w, _ = self.writer(['medulla'], {})
        w.ew.nc.commit_list = lambda batch: False
        with self.assertRaises(RuntimeError):
            w._generate_lookups(self.conf())


if __name__ == '__main__':
    unittest.main()
