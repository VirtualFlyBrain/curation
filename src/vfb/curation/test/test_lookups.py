import unittest
from types import SimpleNamespace
import pandas as pd
from ..curation_writer import record_label_candidates


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


if __name__ == '__main__':
    unittest.main()
