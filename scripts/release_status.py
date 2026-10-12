"""Check release completeness without interpreting API failures as missing releases."""
import json
import os
from pathlib import Path
import urllib.error
import urllib.request


def expected_wheels(entry):
    prefix = entry['distribution'].replace('-', '_') + '-' + entry['package_version']
    return {
        f'{prefix}-{python}-{python}-{platform}.whl'
        for python in ['cp310', 'cp311', 'cp312', 'cp313']
        for platform in ['manylinux_2_17_x86_64.manylinux2014_x86_64',
                         'manylinux_2_17_aarch64.manylinux2014_aarch64',
                         'macosx_14_0_arm64']
    }


def get_release(repo, tag):
    request = urllib.request.Request(f'https://api.github.com/repos/{repo}/releases/tags/{tag}',
        headers={'Authorization': 'Bearer ' + os.environ['GH_TOKEN'], 'Accept': 'application/vnd.github+json'})
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            return json.load(response)
    except urllib.error.HTTPError as error:
        if error.code == 404:
            return None
        raise


def complete(release, entry):
    if release is None or release['draft'] or release['prerelease']:
        return False
    uploaded = {a['name'] for a in release['assets'] if a['state'] == 'uploaded' and a['size'] > 0}
    return expected_wheels(entry) | {'SHA256SUMS'} <= uploaded


if __name__ == '__main__':
    config = json.loads(Path('build-versions.json').read_text())
    pending = [major for major, entry in config['postgres'].items()
               if not complete(get_release(os.environ['GITHUB_REPOSITORY'], entry['release_tag']), entry)]
    print(json.dumps(pending))
    if os.environ.get('GITHUB_OUTPUT'):
        with open(os.environ['GITHUB_OUTPUT'], 'a') as output:
            output.write(f"pending={json.dumps(pending)}\n")
