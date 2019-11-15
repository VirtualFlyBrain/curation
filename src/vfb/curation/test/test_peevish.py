import unittest
from ..peevish import get_recs
import os


class Test_peevish(unittest.TestCase):

    def test_get_recs(self):
        print("\n*** Running from: " + os.getcwd() + "\n\n")
        recs = get_recs(path_to_recs="src/vfb/curation/test/resources/records/new_images/",
                 spec_path="records/")
        for r in recs:
            r.check_working()

if __name__ == '__main__':
    unittest.main()







