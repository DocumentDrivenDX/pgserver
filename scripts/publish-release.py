"""Publish complete wheel sets; never overwrite an existing published release."""
import json
import os
from pathlib import Path
import subprocess
from release_status import complete, expected_wheels, get_release, get_ref


def gh(*args):
    subprocess.run(['gh', *args], check=True)


config = json.loads(Path('build-versions.json').read_text())
entry = config['postgres'][os.environ['PG_MAJOR']]
repo = os.environ['GITHUB_REPOSITORY']
tag = entry['release_tag']
release = get_release(repo, tag)
if complete(release, entry):
    print(f'{tag} is already published; leaving its assets unchanged')
    raise SystemExit(0)
if release is not None and not release['draft']:
    raise SystemExit(f'{tag} is published but incomplete; refusing to overwrite public assets')
assets = sorted(Path('dist').glob('*.whl'))
if {a.name for a in assets} != expected_wheels(entry):
    raise SystemExit('Refusing to publish an incomplete or unexpected wheel set')
if release is None:
    gh('release', 'create', tag, '--repo', repo, '--target', os.environ['SOURCE_SHA'], '--draft', '--generate-notes')
else:
    # An unpublished draft can be retried after a failed upload or CI repair.
    if get_ref(repo, tag) is None:
        # GitHub can defer creating a draft's tag until publication.
        gh('api', f'repos/{repo}/git/refs', '--method', 'POST',
           '-f', 'ref=refs/tags/' + tag, '-f', 'sha=' + os.environ['SOURCE_SHA'])
    else:
        gh('api', f'repos/{repo}/git/refs/tags/{tag}', '--method', 'PATCH',
           '-f', 'sha=' + os.environ['SOURCE_SHA'], '-F', 'force=true')
gh('release', 'upload', tag, *map(str, assets), 'dist/SHA256SUMS', '--repo', repo, '--clobber')
release = get_release(repo, tag)
if not complete(dict(release, draft=False), entry):
    raise SystemExit('Uploaded release is incomplete; keeping it draft')
gh('release', 'edit', tag, '--repo', repo, '--draft=false')
print(f'Published {tag}')
