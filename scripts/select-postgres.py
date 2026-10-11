"""Select a pinned major's source and wheel identity in a clean checkout."""
import json
from pathlib import Path
import re
import sys

root = Path(__file__).resolve().parents[1]
config = json.loads((root / 'build-versions.json').read_text())
major = sys.argv[1]
postgres = config['postgres'][major]
vector = config['pgvector']
if (root / 'src/pgserver/pginstall').exists():
    raise SystemExit('Select a major in a clean checkout: remove the prior native install first.')
makefile = root / 'pgbuild/Makefile'
text = makefile.read_text()
for name, value in {
    'POSTGRES_VERSION': postgres['version'],
    'POSTGRES_SHA256': postgres['sha256'],
    'PGVECTOR_TAG': 'v' + vector['version'],
    'PGVECTOR_SHA256': vector['sha256'],
}.items():
    text, count = re.subn(r'^' + name + r' \?= .+$', name + ' ?= ' + value, text, flags=re.M)
    assert count == 1, name
makefile.write_text(text)
project = root / 'pyproject.toml'
text = project.read_text()
for name, value in {'name': postgres['distribution'], 'version': postgres['package_version']}.items():
    text, count = re.subn(r'^' + name + r' = "[^"]+"', name + ' = "' + value + '"', text, count=1, flags=re.M)
    assert count == 1, name
project.write_text(text)
info = dict(postgres, pgvector_version=vector['version'], postgres_major=major)
(root / 'src/pgserver/_build_info.json').write_text(json.dumps(info, indent=2) + '\n')
print(json.dumps(info))
