import unittest
from powercut import UpdateStore, simulate
class PowerCutTests(unittest.TestCase):
    def test_cut_keeps_previous_active(self):
        result=simulate(4,2)
        self.assertTrue(result["power_cut"]); self.assertEqual(result["active"],"v1"); self.assertTrue(result["recovery"]["consistent"])
    def test_complete_commits(self):
        self.assertEqual(simulate(4)["active"],"v2")

    def test_recovery_ignores_commit_from_previous_update(self):
        store = UpdateStore()
        store.update(2)
        result = store.update(3, cut_after=1)

        self.assertTrue(result["power_cut"])
        self.assertEqual(result["active"], "v2")
        recovery = store.recover()
        self.assertIsNone(recovery["staged"])
        self.assertTrue(recovery["consistent"])

    def test_invalid_power_cut_point_is_rejected(self):
        with self.assertRaises(ValueError):
            simulate(4, cut_after=0)
        with self.assertRaises(ValueError):
            simulate(4, cut_after=5)

    def test_empty_update_is_rejected(self):
        with self.assertRaises(ValueError):
            simulate(0)
if __name__=="__main__": unittest.main()
