import unittest
from powercut import simulate
class PowerCutTests(unittest.TestCase):
    def test_cut_keeps_previous_active(self):
        result=simulate(4,2)
        self.assertTrue(result["power_cut"]); self.assertEqual(result["active"],"v1"); self.assertTrue(result["recovery"]["consistent"])
    def test_complete_commits(self):
        self.assertEqual(simulate(4)["active"],"v2")
if __name__=="__main__": unittest.main()
