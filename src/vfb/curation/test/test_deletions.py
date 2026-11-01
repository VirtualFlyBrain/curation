import unittest
from ..deletion_cypher import deletion_statements
from ..peevish import get_recs

RELATIONS = {'is_a': {'type': 'subClassOf'},
             'has_soma_location': {'type': 'objectProperty', 'short_form': 'RO_0002100'},
             'has_presynaptic_terminal_in': {'type': 'objectProperty', 'short_form': 'RO_0002113'},
             'no_id': {'type': 'objectProperty'}}


class TestDeletionCypher(unittest.TestCase):

    def test_is_a_maps_to_instanceof(self):
        statements, failures = deletion_statements(
            [{'Individual_id': 'VFB_jrmc2zmq', 'relation': 'is_a', 'remove': 'FBbt_00052753'}],
            RELATIONS, delete=True)
        self.assertEqual(failures, [])
        self.assertEqual(statements[0][1],
                         "MATCH (i:Individual {short_form: 'VFB_jrmc2zmq'})-[r:INSTANCEOF]->"
                         "(o {short_form: 'FBbt_00052753'}) DELETE r RETURN count(r) AS n")

    def test_object_property_matched_by_id(self):
        # edge type names don't always match the relation (has_presynaptic_terminals_in in the KB)
        statements, _ = deletion_statements(
            [{'Individual_id': 'VFB_a', 'relation': 'has_soma_location', 'remove': 'FBbt_1'},
             {'Individual_id': 'VFB_a', 'relation': 'has_presynaptic_terminal_in', 'remove': 'FBbt_2'}],
            RELATIONS)
        self.assertEqual(statements[0][1],
                         "MATCH (i:Individual {short_form: 'VFB_a'})-[r]->(o {short_form: 'FBbt_1'}) "
                         "WHERE r.short_form = 'RO_0002100' RETURN count(r) AS n")
        self.assertIn("r.short_form = 'RO_0002113'", statements[1][1])
        self.assertNotIn('DELETE', statements[0][1])

    def test_bad_rows_fail(self):
        rows = [{'Individual_id': "VFB_a'}) DETACH DELETE i //", 'relation': 'is_a', 'remove': 'FBbt_1'},
                {'Individual_id': 'VFB_a', 'relation': 'is_a', 'remove': 'FBbt:00000001'},
                {'Individual_id': 'VFB_a', 'relation': 'part_of', 'remove': 'FBbt_1'},
                {'Individual_id': 'VFB_a', 'relation': 'no_id', 'remove': 'FBbt_1'}]
        statements, failures = deletion_statements(rows, RELATIONS)
        self.assertEqual(statements, [])
        self.assertEqual([f['context_name'] for f in failures],
                         ['Individual_id', 'remove', 'relation', 'relation'])

    def test_record_syntax(self):
        recs = get_recs(path_to_recs="src/vfb/curation/test/resources/records/newmeta_deletions/working/",
                        spec_path="records/newmeta_deletions")
        self.assertEqual(len(recs), 1)
        self.assertTrue(recs[0])


if __name__ == '__main__':
    unittest.main()
