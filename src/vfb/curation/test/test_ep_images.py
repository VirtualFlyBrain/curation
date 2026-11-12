import unittest
from unittest import mock

from ..curation_writer import NewImageWriter


class TestEpImageRows(unittest.TestCase):
    """new_images ep rows make the driver's expression pattern class."""

    def test_driver_passed_as_a_list(self):
        w = object.__new__(NewImageWriter)
        w.record = mock.Mock()
        w.record.type = 'ep'
        w.record.spec = {}
        w.record.rel_spec = {}
        w.object_lookup = {'driver': {'P{GMR10A01-GAL4}': 'FBtp0000001'}}
        w.feature_mover = mock.Mock()
        w.failures, w.stat = [], True
        out = w.gen_pw_args({'driver': 'P{GMR10A01-GAL4}'}, start='100000')
        w.feature_mover.generate_expression_patterns.assert_called_once_with(['FBtp0000001'], commit=False)
        self.assertEqual(out['anatomical_type'], 'VFBexp_FBtp0000001')


if __name__ == '__main__':
    unittest.main()
