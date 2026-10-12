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


def get_json(path):
    request = urllib.request.Request(f'https://api.github.com/{path}',
        headers={'Authorization': 'Bearer ' + os.environ['GH_TOKEN'], 'Accept': 'application/vnd.github+json'})
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            return json.load(response)
    except urllib.error.HTTPError as error:
        if error.code == 404:
            return None
        raise


def get_release(repo, tag):
    release = get_json(f'repos/{repo}/releases/tags/{tag}')
    if release is not None:
        return release
    # The tag endpoint returns published releases only. Drafts are available
    # to the repository token through the paginated releases collection.
    page = 1
    while True:
        releases = get_json(f'repos/{repo}/releases?per_page=100&page={page}')
        for entry in releases:
            if entry['tag_name'] == tag:
                return entry
        if len(releases) < 100:
            return None
        page += 1


def get_ref(repo, tag):
    return get_json(f'repos/{repo}/git/ref/tags/{tag}')


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
