import unittest

from powercut import UpdateStore


class AutoVersionHistoryTests(unittest.TestCase):
    def test_auto_version_skips_numeric_history_after_custom_release(self):
        store = UpdateStore()
        store.update(1, target_version="v4")
        store.update(1, target_version="release-custom")
        self.assertEqual(store.update(1)["active"], "v5")
        self.assertEqual(store.update(1)["active"], "v6")

    def test_auto_version_stays_above_highest_committed_numeric_version(self):
        store = UpdateStore()
        store.update(1, target_version="v100")
        store.update(1, target_version="release-custom")
        self.assertEqual(store.update(1)["active"], "v101")

    def test_lower_active_numeric_label_does_not_hide_history(self):
        store = UpdateStore()
        store.update(1, target_version="v100")
        store.update(1, target_version="v2")
        self.assertEqual(store.update(1)["active"], "v101")

    def test_custom_release_sequence_keeps_transaction_count_baseline(self):
        store = UpdateStore()
        store.update(1, target_version="release-a")
        store.update(1, target_version="release-b")
        self.assertEqual(store.update(1)["active"], "v4")

    def test_aborted_numeric_target_does_not_advance_committed_history(self):
        store = UpdateStore()
        result = store.update(1, cut_after=1, target_version="v100")
        self.assertTrue(result["power_cut"])
        self.assertNotIn("v100", store.committed_versions)
        self.assertEqual(store.update(1)["active"], "v2")


if __name__ == "__main__":
    unittest.main()
