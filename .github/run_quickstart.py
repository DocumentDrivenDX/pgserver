"""Run the README quickstart: the python block between <!-- quickstart --> markers."""
import argparse
import re
import subprocess
import sys
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument('readme')
parser.add_argument('--expect', help='substring that must appear in the output')
args = parser.parse_args()
text = Path(args.readme).read_text()
match = re.search(r'<!-- quickstart -->\s*```python\n(.*?)```\s*<!-- /quickstart -->', text, re.S)
if not match:
    sys.exit('quickstart block not found in ' + args.readme)
result = subprocess.run([sys.executable, '-c', match.group(1)], capture_output=True, text=True, timeout=300)
print(result.stdout)
print(result.stderr, file=sys.stderr)
if result.returncode:
    sys.exit(f'quickstart failed with exit code {result.returncode}')
if args.expect and args.expect not in result.stdout:
    sys.exit(f'expected {args.expect!r} in quickstart output')
