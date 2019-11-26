import unittest
from ..cur_load import Annotate, VfbInd, LConf


class TestVFbInd(unittest.TestCase):

    def test_label_id(self):
        VfbInd(label='fu', id='VFB_00000015')

    # Add negative test?

    def test_xref(self):
        t = VfbInd(xref='FBsite_FlyCircuit:fru-M-900048')


class TestCurationWriter(unittest.TestCase):

    def setUp(self):
        lc = {'overlaps': [LConf(field='short_form', regex='FBbt_.+', labels=['Class'])],
              'subject': [LConf(field='short_form', regex='VFB_.+', labels=['Individual'])]}
        rl = {'overlaps': 'RO_0002131'}
        self.aw = Annotate('http://localhost:7474', 'neo4j', 'neo4j',
                                 lookup_config=lc,
                                 relation_lookup=rl)


    def test_add_annotation_name_id_true(self):
        s = VfbInd(id='VFB_00000015', label='fru-M-900048')
        self.aw.add_assertion_to_VFB_ind(s, r='overlaps', o='lateral horn', edge_annotations={'comment': 'Ipsum lorem.'})
        assert bool(self.aw.commit())is True


    def test_add_annotation_name_id_false (self):
        s = VfbInd(id='VFB_000000015', label='fru-M-900048')
        self.aw.add_assertion_to_VFB_ind(s, r='overlaps', o='lateral horn', edge_annotations={'comment': 'Ipsum lorem.'})
        assert bool(self.aw.commit())is False


if __name__ == '__main__':
    unittest.main()
