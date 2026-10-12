"""Discover stable minor releases from PostgreSQL and verify source before pinning."""
import argparse
from datetime import date
import hashlib
import json
from pathlib import Path
import re
import urllib.request
import xml.etree.ElementTree as ET

FEED = 'https://www.postgresql.org/versions.rss'
SOURCE = 'https://ftp.postgresql.org/pub/source'


def fetch(url):
    request = urllib.request.Request(url, headers={'User-Agent': 'DocumentDrivenDX-pgserver-updater'})
    return urllib.request.urlopen(request, timeout=120)


def stable_versions(feed, majors):
    found = {}
    for item in ET.fromstring(feed).findall('./channel/item'):
        version = (item.findtext('title') or '').strip()
        if not re.fullmatch(r'(16|17|18)\.\d+', version):
            continue
        major, minor = version.split('.')
        if major in majors and (major not in found or int(minor) > int(found[major].split('.')[1])):
            found[major] = version
    if set(found) != set(majors):
        raise ValueError('Official feed is missing a tracked stable major')
    return found


def source_checksum(version):
    filename = f'postgresql-{version}.tar.gz'
    url = f'{SOURCE}/v{version}/{filename}'
    with fetch(url + '.sha256') as response:
        text = response.read().decode().strip()
    match = re.fullmatch(r'([a-fA-F0-9]{64})\s+\*?' + re.escape(filename), text)
    if not match:
        raise ValueError(f'Invalid official checksum for {version}')
    expected = match[1].lower()
    digest = hashlib.sha256()
    with fetch(url) as response:
        for chunk in iter(lambda: response.read(1024 * 1024), b''):
            digest.update(chunk)
    if digest.hexdigest() != expected:
        raise ValueError(f'Official source checksum mismatch for {version}')
    return expected


def update_config(config, latest, checksum):
    # Work on a copy; no partial pin updates if any source validation fails.
    result = json.loads(json.dumps(config))
    changed = []
    for major, entry in result['postgres'].items():
        version = latest[major]
        previous = entry['version']
        if tuple(map(int, version.split('.'))) < tuple(map(int, previous.split('.'))):
            raise ValueError(f'Refusing downgrade {previous} -> {version}')
        if version == previous:
            continue
        entry.update(version=version, sha256=checksum(version),
                     package_version=version + '.0',
                     release_tag=f"pg{version}-pgv{result['pgvector']['version']}")
        changed.append(major)
    return result, changed


def save_config(root, config):
    # Keep default source/package metadata in sync with the default PG18 entry.
    pg = config['postgres']['18']
    vector = config['pgvector']
    makefile = root / 'pgbuild/Makefile'
    text = makefile.read_text()
    for name, value in {'POSTGRES_VERSION': pg['version'], 'POSTGRES_SHA256': pg['sha256']}.items():
        text, count = re.subn(r'^' + name + r' \?= .+$', name + ' ?= ' + value, text, flags=re.M)
        if count != 1:
            raise ValueError(f'Missing Makefile setting {name}')
    project = root / 'pyproject.toml'
    project_text, count = re.subn(r'^version = "[^"]+"', f"version = \"{pg['package_version']}\"", project.read_text(), count=1, flags=re.M)
    if count != 1:
        raise ValueError('Missing package version')
    readme = root / 'README.md'
    readme_text = readme.read_text()
    for major, entry in config['postgres'].items():
        readme_text = re.sub(r'^\| ' + major + r'\.\d+ \|.*$',
            f"| {entry['version']} | `{entry['distribution']}` | `{entry['package_version']}` | {vector['version']} |", readme_text, flags=re.M)
    # Validation is complete before any repository file is written.
    (root / 'build-versions.json').write_text(json.dumps(config, indent=2) + '\n')
    makefile.write_text(text)
    project.write_text(project_text)
    info = dict(pg, pgvector_version=vector['version'], postgres_major='18')
    (root / 'src/pgserver/_build_info.json').write_text(json.dumps(info, indent=2) + '\n')
    readme.write_text(readme_text)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    config = json.loads((args.root / 'build-versions.json').read_text())
    with fetch(FEED) as response:
        latest = stable_versions(response.read(), config['postgres'])
    result, changed = update_config(config, latest, source_checksum)
    if changed:
        save_config(args.root, result)
    # Public scheduled workflows are disabled after 60 days without repository
    # activity; keep a monthly verification receipt between quarterly releases.
    state_path = args.root / '.github/postgres-update-state.json'
    today = date.today()
    state = json.loads(state_path.read_text()) if state_path.exists() else {}
    last = date.fromisoformat(state['last_checked']) if state else None
    if changed or last is None or (today - last).days >= 30:
        state_path.parent.mkdir(parents=True, exist_ok=True)
        state_path.write_text(json.dumps({'last_checked': today.isoformat(), 'versions': latest}, indent=2) + '\n')
    print(json.dumps({'changed': changed, 'versions': latest}))


if __name__ == '__main__':
    main()
