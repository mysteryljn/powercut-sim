import contextlib
import io
import unittest
from powercut import MAX_CHUNKS, UpdateStore, main, simulate
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

    def test_recovery_finishes_commit_before_activation(self):
        # This is the durable state left by a power loss between writing the
        # commit marker and switching the active version pointer.
        store = UpdateStore()
        store.staged = "v2"
        store.journal = ["stage", "write:0", "commit"]

        recovery = store.recover()

        self.assertEqual(recovery["active"], "v2")
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

    def test_oversized_update_is_rejected(self):
        # A caller-controlled chunk count must not permit unbounded journal
        # growth and CPU use.
        with self.assertRaises(ValueError):
            simulate(MAX_CHUNKS + 1)

    def test_repeated_updates_advance_version(self):
        store = UpdateStore()
        self.assertEqual(store.update(2)["active"], "v2")
        self.assertEqual(store.update(2)["active"], "v3")

    def test_auto_version_does_not_reuse_after_custom_release(self):
        store = UpdateStore()
        self.assertEqual(store.update(1)["active"], "v2")
        self.assertEqual(
            store.update(1, target_version="release-2026.10")["active"],
            "release-2026.10",
        )

        # The old generator fell back to v2 for a non-vN active label,
        # reactivating an already committed image on the next update.
        self.assertEqual(store.update(1)["active"], "v4")

    def test_target_version_can_be_selected(self):
        store = UpdateStore()
        result = store.update(1, target_version="release-2026.10")
        self.assertEqual(result["active"], "release-2026.10")

    def test_target_version_cannot_match_active(self):
        with self.assertRaises(ValueError):
            simulate(1, target_version="v1")

    def test_target_version_cannot_reuse_committed_release(self):
        store = UpdateStore()
        self.assertEqual(store.update(1)["active"], "v2")
        self.assertEqual(store.update(1)["active"], "v3")
        with self.assertRaisesRegex(ValueError, "already committed"):
            store.update(1, target_version="v2")

    def test_cli_reports_invalid_target_version_without_traceback(self):
        for target in ("v1", "   "):
            output = io.StringIO()
            with self.subTest(target=target), contextlib.redirect_stdout(output):
                self.assertEqual(main(["--chunks", "1", "--target-version", target]), 2)
            self.assertIn("error:", output.getvalue())

if __name__=="__main__": unittest.main()
