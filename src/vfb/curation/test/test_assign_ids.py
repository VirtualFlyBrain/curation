import importlib.util
import os
import tempfile
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location('assign_ids', os.path.join(HERE, '..', '..', '..', 'assign_ids.py'))
assign_ids = importlib.util.module_from_spec(spec)
spec.loader.exec_module(assign_ids)


class TestAssign(unittest.TestCase):

    def write(self, d, name, text, yaml_text=None):
        p = os.path.join(d, name)
        with open(p, 'w', newline='') as f:
            f.write(text)
        if yaml_text is not None:
            with open(os.path.splitext(p)[0] + '.yaml', 'w') as f:
                f.write(yaml_text)
        return p

    def pw(self, ids):
        m = mock.Mock()
        m.reserve_image_ids.side_effect = lambda start, n, who: ids[:n]
        return m

    def test_adds_column_and_fills_only_empty_rows(self):
        with tempfile.TemporaryDirectory() as d:
            p = self.write(d, 'anat_x.tsv', 'label\tfilename\na\ta.nrrd\nb\tb.nrrd\n', 'Start: 200\n')
            pw = self.pw(['VFB_00000200', 'VFB_00000201'])
            self.assertTrue(assign_ids.assign(p, pw, 'Clare72_curation'))
            with open(p, newline='') as f:
                self.assertEqual('label\tfilename\tanat_id\na\ta.nrrd\tVFB_00000200\nb\tb.nrrd\tVFB_00000201\n', f.read())
            pw.reserve_image_ids.assert_called_once_with('200', 2, 'Clare72_curation:anat_x.tsv')

    def test_keeps_given_ids_and_line_endings(self):
        with tempfile.TemporaryDirectory() as d:
            p = self.write(d, 'anat_x.tsv', 'anat_id\tlabel\r\nVFB_00000999\ta\r\n\tb\r\n')
            self.assertTrue(assign_ids.assign(p, self.pw(['VFB_00000300']), 'r'))
            with open(p, newline='') as f:
                self.assertEqual('anat_id\tlabel\r\nVFB_00000999\ta\r\nVFB_00000300\tb\r\n', f.read())

    def test_nothing_to_do(self):
        with tempfile.TemporaryDirectory() as d:
            p = self.write(d, 'anat_x.tsv', 'anat_id\tlabel\nVFB_00000999\ta\n')
            pw = self.pw([])
            self.assertFalse(assign_ids.assign(p, pw, 'r'))
            pw.reserve_image_ids.assert_not_called()

    def test_failed_reservation_leaves_file_unchanged(self):
        with tempfile.TemporaryDirectory() as d:
            text = 'label\na\n'
            p = self.write(d, 'anat_x.tsv', text)
            pw = mock.Mock()
            pw.reserve_image_ids.side_effect = RuntimeError('no KB')
            with self.assertRaises(RuntimeError):
                assign_ids.assign(p, pw, 'r')
            with open(p, newline='') as f:
                self.assertEqual(text, f.read())


if __name__ == '__main__':
    unittest.main()
