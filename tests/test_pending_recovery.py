import unittest

from powercut import MAX_CHUNKS, UpdateStore


def pending_commit(version="v2"):
    store = UpdateStore()
    store.staged = version
    store.journal = ["stage", "write:0", "commit"]
    return store


def state(store):
    return store.active, store.staged, list(store.journal), set(store.committed_versions)


class PendingRecoveryTests(unittest.TestCase):
    def test_new_cut_preserves_previous_durable_commit(self):
        store = pending_commit()
        result = store.update(1, cut_after=1)
        self.assertTrue(result["power_cut"])
        self.assertEqual(result["active"], "v2")
        self.assertEqual(store.committed_versions, {"v1", "v2"})
        self.assertIsNone(store.staged)
        self.assertEqual(store.recover()["active"], "v2")

    def test_successful_update_retains_pending_commit_in_history(self):
        store = pending_commit()
        self.assertEqual(store.update(1)["active"], "v3")
        self.assertEqual(store.committed_versions, {"v1", "v2", "v3"})
        with self.assertRaisesRegex(ValueError, "already committed"):
            store.update(1, target_version="v2")

    def test_auto_target_is_chosen_after_pending_activation(self):
        store = pending_commit("v20")
        self.assertEqual(store.update(1)["active"], "v21")
        self.assertEqual(store.committed_versions, {"v1", "v20", "v21"})

    def test_pending_target_cannot_be_recommitted(self):
        store = pending_commit()
        before = state(store)
        with self.assertRaises(ValueError):
            store.update(1, target_version="v2")
        self.assertEqual(state(store), before)
        self.assertEqual(store.recover()["active"], "v2")

    def test_invalid_arguments_preserve_recoverable_transaction(self):
        invalid_calls = (
            {"chunks": 0},
            {"chunks": True},
            {"chunks": MAX_CHUNKS + 1},
            {"chunks": 1, "cut_after": 2},
            {"chunks": 1, "target_version": "   "},
            {"chunks": 1, "target_version": []},
            {"chunks": 1, "target_version": "v1"},
        )
        for arguments in invalid_calls:
            with self.subTest(arguments=arguments):
                store = pending_commit()
                before = state(store)
                with self.assertRaises(ValueError):
                    store.update(**arguments)
                self.assertEqual(state(store), before)
                self.assertEqual(store.recover()["active"], "v2")

    def test_uncommitted_staged_target_can_be_retried(self):
        store = pending_commit()
        store.journal.pop()  # Power loss before the durable commit marker.
        self.assertEqual(store.update(1, target_version="v2")["active"], "v2")
        self.assertEqual(store.committed_versions, {"v1", "v2"})


if __name__ == "__main__":
    unittest.main()
