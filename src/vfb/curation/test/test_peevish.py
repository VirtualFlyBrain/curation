import unittest
from ..peevish import get_recs
import os


class Test_tsv_headers(unittest.TestCase):

    def test_get_recs(self):
        print(os.getcwd())
        recs = get_recs(path_to_recs="src/vfb/curation/test/resources/records/new_images/",
                 spec_path="records/")
        for r in recs:
            r.check_working()






