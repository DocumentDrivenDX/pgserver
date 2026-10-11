import hashlib
import sys
from pathlib import Path

path, expected = sys.argv[1:]
actual = hashlib.sha256(Path(path).read_bytes()).hexdigest()
if actual != expected:
    raise SystemExit(f"SHA256 mismatch for {path}: {actual} != {expected}")
print(f"Verified {path}: {actual}")
