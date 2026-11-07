"""Verify a downloaded Wan pilot export before any media enters a production candidate."""
import argparse,json
from .worker import import_export
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('archive');p.add_argument('destination');p.add_argument('--sha256',required=True);p.add_argument('--job',required=True);a=p.parse_args()
 print(json.dumps(import_export(a.archive,a.destination,a.sha256,a.job),indent=2))
