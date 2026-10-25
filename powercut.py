#!/usr/bin/env python3
import argparse
import json
class UpdateStore:
    def __init__(self):
        self.active="v1"; self.staged=None; self.journal=[]
    def update(self,chunks,cut_after=None):
        if not isinstance(chunks, int) or isinstance(chunks, bool) or chunks < 1:
            raise ValueError("chunks must be a positive integer")
        if cut_after is not None and (
            not isinstance(cut_after, int) or isinstance(cut_after, bool)
            or not 1 <= cut_after <= chunks
        ):
            raise ValueError("cut_after must be within chunks")
        self.staged="v2"; self.journal.append("stage")
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
        committed = last_stage is None or any(
            entry == "commit" for entry in self.journal[last_stage + 1:]
        )
        if not committed: self.staged=None
        return {"active":self.active,"staged":self.staged,"consistent":self.staged is None or committed}
def simulate(chunks,cut_after=None):
    store=UpdateStore(); result=store.update(chunks,cut_after)
    result["recovery"]=store.recover(); return result
def main(argv=None):
    p=argparse.ArgumentParser(description="Simulate power loss during a software update"); p.add_argument("--chunks",type=int,required=True); p.add_argument("--cut-after",type=int); a=p.parse_args(argv)
    if a.chunks<1 or a.cut_after is not None and not 1<=a.cut_after<=a.chunks: p.error("cut-after must be within chunks")
    print(json.dumps(simulate(a.chunks,a.cut_after),indent=2)); return 0
if __name__=="__main__": raise SystemExit(main())
