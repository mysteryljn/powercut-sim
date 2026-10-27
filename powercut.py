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
    @staticmethod
    def _next_version(active, committed_updates=0):
        match = re.match(r"^v(\d+)$", active)
        # A custom release label may be active after one or more committed
        # updates.  Falling back to v2 in that state can reuse an older
        # automatically generated version (for example v1 -> v2 -> release
        # -> v2), which makes a later update indistinguishable from a stale
        # image.  Keep the generated sequence ahead of both the active
        # numeric version and the number of committed transactions.
        next_number = committed_updates + 2
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
        if target_version is None:
            target_version = self._next_version(
                self.active, self.journal.count("commit")
            )
        if (not isinstance(target_version, str) or not target_version.strip()
                or target_version == self.active):
            raise ValueError("target_version must be a non-empty version different from active")
        self.staged=target_version; self.journal.append("stage")
        for index in range(chunks):
            self.journal.append("write:%d"%index)
            if cut_after is not None and index+1==cut_after:
                return {"power_cut":True,"active":self.recover()["active"],"journal":list(self.journal)}
        self.journal.append("commit"); self.active=self.staged; self.staged=None
        return {"power_cut":False,"active":self.active,"journal":list(self.journal)}
    def recover(self):
        # A commit from an earlier update must not make a later, interrupted
        # transaction look committed.  Only a commit after the most recent
        # stage belongs to the currently recoverable transaction.
        last_stage = next((index for index in range(len(self.journal) - 1, -1, -1)
                           if self.journal[index] == "stage"), None)
        committed = last_stage is not None and any(
            entry == "commit" for entry in self.journal[last_stage + 1:]
        )
        if committed and self.staged is not None:
            # A power loss can happen after the durable commit marker is
            # written but before the active pointer is switched.  Finish the
            # activation during recovery instead of silently running v1.
            self.active = self.staged
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
    print(json.dumps(simulate(a.chunks,a.cut_after,a.target_version),indent=2)); return 0
if __name__=="__main__": raise SystemExit(main())
