"""Portable entry; algorithm and original-oracle hash remain unchanged."""
from pathlib import Path
import argparse,json
import placement_rescore_v11 as oracle
oracle.SUPPORT=Path(__file__).parent/'frozen_strict'
oracle.ORACLE=oracle.SUPPORT/'audit_whole_t3_stream_liveness_v11.py'
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('trace');p.add_argument('--expected-rows',type=int);p.add_argument('--output');a=p.parse_args();value=oracle.rescore(a.trace,a.expected_rows);text=json.dumps(value,indent=2)
 if a.output:Path(a.output).write_text(text+'\n')
 print(text)
