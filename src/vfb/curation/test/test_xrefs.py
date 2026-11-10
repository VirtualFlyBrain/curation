import unittest
from ..xref_cypher import xref_rows, check_statement
from ..peevish import get_recs


class TestXrefCypher(unittest.TestCase):

    def test_accession_with_colon(self):
        checked, failures = xref_rows([{'Individual_id': 'VFB_jrmc2zmq', 'site': 'neuronbridge',
                                        'accession': 'male-cns:166793'}])
        self.assertEqual(failures, [])
        self.assertEqual(checked[0][1:4], ('VFB_jrmc2zmq', 'neuronbridge', 'male-cns:166793'))
        self.assertIn("WHERE r.accession = ['male-cns:166793']", checked[0][4])
        self.assertNotIn('MERGE', checked[0][4])
        self.assertNotIn('DELETE', checked[0][4])

    def test_site_with_hyphen(self):
        self.assertIn("{short_form: 'male-cns_v0_9'}", check_statement('VFB_a', 'male-cns_v0_9', '1'))
        _, failures = xref_rows([{'Individual_id': 'VFB_a', 'site': 'male-cns_v0_9', 'accession': '1'}])
        self.assertEqual(failures, [])

    def test_bad_rows_fail(self):
        rows = [{'Individual_id': "VFB_a'}) DETACH DELETE i //", 'site': 'neuronbridge', 'accession': '1'},
                {'Individual_id': 'VFB_a', 'site': "x'}) DELETE s //", 'accession': '1'},
                {'Individual_id': 'VFB_a', 'site': 'neuronbridge', 'accession': "1'] DELETE r //"},
                {'Individual_id': 'VFB_a', 'site': 'neuronbridge', 'accession': ''}]
        checked, failures = xref_rows(rows)
        self.assertEqual(checked, [])
        self.assertEqual([f['context_name'] for f in failures], ['Individual_id', 'site', 'accession', 'accession'])

    def test_record_syntax(self):
        recs = get_recs(path_to_recs="src/vfb/curation/test/resources/records/new_xrefs/working/",
                        spec_path="records/new_xrefs")
        self.assertEqual(len(recs), 1)
        self.assertTrue(recs[0])
        self.assertEqual(recs[0].gross_type, 'new_xrefs')


if __name__ == '__main__':
    unittest.main()
