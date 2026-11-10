#!/usr/bin/env python3
import argparse
import json
import re

# Keep untrusted CLI/API input from allocating an unbounded journal or
# spending an unbounded amount of CPU in the simulation loop.
MAX_CHUNKS = 100000

class UpdateStore:
    def __init__(self):
        self.active="v1"; self.staged=None; self.journal=[]
        # Keep committed identities separate from the active pointer so an
        # explicitly requested target cannot replay an older image after a
        # later release became active.
        self.committed_versions={self.active}
    @staticmethod
    def _next_version(active, committed_updates=0, committed_versions=()):
        # Custom labels and explicitly selected numeric versions can hide a
        # higher number in committed history.  Keep automatic versions above
        # that history as well as the existing transaction-count baseline.
        next_number = committed_updates + 2
        for version in set(committed_versions) | {active}:
            match = re.match(r"^v(\d+)$", version)
            if match:
                next_number = max(next_number, int(match.group(1)) + 1)
        return "v%d" % next_number
    def update(self,chunks,cut_after=None,target_version=None):
        if not isinstance(chunks, int) or isinstance(chunks, bool) or chunks < 1:
            raise ValueError("chunks must be a positive integer")
        if chunks > MAX_CHUNKS:
            raise ValueError("chunks must not exceed %d" % MAX_CHUNKS)
        if cut_after is not None and (
            not isinstance(cut_after, int) or isinstance(cut_after, bool)
            or not 1 <= cut_after <= chunks
        ):
            raise ValueError("cut_after must be within chunks")
        # Validate against the state recovery will activate, without changing
        # the pending transaction if the new request turns out to be invalid.
        recovered_active = self.active
        if self.staged is not None and self._has_committed_stage():
            recovered_active = self.staged
        recovered_versions = self.committed_versions | {recovered_active}
        if target_version is None:
            target_version = self._next_version(
                recovered_active, self.journal.count("commit"), recovered_versions
            )
        if (not isinstance(target_version, str) or not target_version.strip()
                or target_version == recovered_active):
            raise ValueError("target_version must be a non-empty version different from active")
        if target_version in recovered_versions:
            raise ValueError("target_version was already committed")
        # A durable commit must be activated before staged is reused.  A cut
        # in the new update must retain that committed version and its history.
        self.recover()
        self.staged=target_version; self.journal.append("stage")
        for index in range(chunks):
            self.journal.append("write:%d"%index)
            if cut_after is not None and index+1==cut_after:
                return {"power_cut":True,"active":self.recover()["active"],"journal":list(self.journal)}
        self.journal.append("commit"); self.active=self.staged; self.committed_versions.add(self.active); self.staged=None
        return {"power_cut":False,"active":self.active,"journal":list(self.journal)}
    def _has_committed_stage(self):
        # A commit from an earlier update must not make a later, interrupted
        # transaction look committed.  Only a commit after the most recent
        # stage belongs to the currently recoverable transaction.
        last_stage = next((index for index in range(len(self.journal) - 1, -1, -1)
                           if self.journal[index] == "stage"), None)
        return last_stage is not None and any(
            entry == "commit" for entry in self.journal[last_stage + 1:]
        )
    def recover(self):
        committed = self._has_committed_stage()
        if committed and self.staged is not None:
            # A power loss can happen after the durable commit marker is
            # written but before the active pointer is switched.  Finish the
            # activation during recovery instead of silently running v1.
            self.active = self.staged
            self.committed_versions.add(self.active)
            self.staged = None
        elif not committed:
            self.staged=None
        return {"active":self.active,"staged":self.staged,"consistent":self.staged is None}
def simulate(chunks,cut_after=None,target_version=None):
    store=UpdateStore(); result=store.update(chunks,cut_after,target_version)
    result["recovery"]=store.recover(); return result
def main(argv=None):
    p=argparse.ArgumentParser(description="Simulate power loss during a software update"); p.add_argument("--chunks",type=int,required=True); p.add_argument("--cut-after",type=int); p.add_argument("--target-version"); a=p.parse_args(argv)
    if a.chunks < 1 or a.chunks > MAX_CHUNKS:
        p.error("chunks must be between 1 and %d" % MAX_CHUNKS)
    if a.cut_after is not None and not 1<=a.cut_after<=a.chunks: p.error("cut-after must be within chunks")
    try:
        result=simulate(a.chunks,a.cut_after,a.target_version)
    except ValueError as exc:
        # Target-version and transaction validation errors are expected input
        # failures.  Report them through the CLI contract instead of leaking
        # a traceback from the simulator.
        print("error: "+str(exc))
        return 2
    print(json.dumps(result,indent=2)); return 0
if __name__=="__main__": raise SystemExit(main())
