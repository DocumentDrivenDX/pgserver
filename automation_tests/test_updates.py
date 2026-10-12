import copy
import importlib.util
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('update_postgres', ROOT / 'scripts/update-postgres.py')
updater = importlib.util.module_from_spec(spec)
spec.loader.exec_module(updater)
sys.path.insert(0, str(ROOT / 'scripts'))
from release_status import complete, expected_wheels


class ReleaseUpdates(unittest.TestCase):
    def setUp(self):
        self.config = json.loads((ROOT / 'build-versions.json').read_text())
        self.latest = {major: entry['version'] for major, entry in self.config['postgres'].items()}

    def test_current_releases_do_not_download_or_change_pins(self):
        result, changed = updater.update_config(self.config, self.latest, lambda v: self.fail('Unexpected source download'))
        self.assertEqual(result, self.config)
        self.assertEqual(changed, [])

    def test_new_minor_gets_new_identity_and_official_checksum(self):
        major = '17'
        minor = int(self.latest[major].split('.')[1]) + 1
        self.latest[major] = f'{major}.{minor}'
        result, changed = updater.update_config(self.config, self.latest, lambda v: 'a' * 64)
        self.assertEqual(changed, ['17'])
        self.assertEqual(result['postgres']['17']['sha256'], 'a' * 64)
        self.assertEqual(result['postgres']['17']['package_version'], f'17.{minor}.0')
        self.assertEqual(result['postgres']['17']['release_tag'], f"pg17.{minor}-pgv{self.config['pgvector']['version']}")
        self.assertEqual(result['postgres']['18'], self.config['postgres']['18'])
        self.assertNotEqual(result['postgres']['17'], self.config['postgres']['17'])

    def test_prereleases_and_untracked_majors_are_ignored(self):
        feed = '<rss><channel>' + ''.join(f'<item><title>{version}</title></item>' for version in [*self.latest.values(), '18.99beta1', '19.0', '17.999rc1']) + '</channel></rss>'
        self.assertEqual(updater.stable_versions(feed, self.latest), self.latest)

    def test_missing_major_and_downgrade_fail_closed(self):
        with self.assertRaises(ValueError):
            updater.stable_versions('<rss><channel/></rss>', self.latest)
        self.latest['16'] = '16.0'
        with self.assertRaises(ValueError):
            updater.update_config(self.config, self.latest, lambda v: 'a' * 64)

    def test_failed_verification_does_not_change_original_config(self):
        original = copy.deepcopy(self.config)
        self.latest = {major: f'{major}.{int(version.split(".")[1]) + 1}' for major, version in self.latest.items()}
        def checksum(version):
            if version.startswith('17.'):
                raise ValueError('Source checksum mismatch')
            return 'a' * 64
        with self.assertRaises(ValueError):
            updater.update_config(self.config, self.latest, checksum)
        self.assertEqual(self.config, original)

    def test_complete_release_requires_every_python_and_platform(self):
        entry = self.config['postgres']['18']
        names = expected_wheels(entry) | {'SHA256SUMS'}
        release = {'draft': False, 'prerelease': False, 'assets': [{'name': name, 'state': 'uploaded', 'size': 10} for name in names]}
        self.assertTrue(complete(release, entry))
        release['assets'].pop()
        self.assertFalse(complete(release, entry))
        self.assertFalse(complete(None, entry))
        release['draft'] = True
        self.assertFalse(complete(release, entry))


if __name__ == '__main__':
    unittest.main()

class SourceIntegrity(unittest.TestCase):
    def test_source_hash_mismatch_is_rejected(self):
        import io
        with patch.object(updater, 'fetch', side_effect=[io.BytesIO(b'a' * 64 + b'  postgresql-17.99.tar.gz'), io.BytesIO(b'corrupt source')]):
            with self.assertRaisesRegex(ValueError, 'checksum mismatch'):
                updater.source_checksum('17.99')

    def test_valid_official_archive_is_accepted(self):
        import hashlib
        import io
        data = b'verified source fixture'
        digest = hashlib.sha256(data).hexdigest()
        with patch.object(updater, 'fetch', side_effect=[io.BytesIO((digest + '  postgresql-17.99.tar.gz').encode()), io.BytesIO(data)]):
            self.assertEqual(updater.source_checksum('17.99'), digest)

class PinPersistence(unittest.TestCase):
    def test_default_pg18_files_and_readme_follow_updated_pins(self):
        import shutil
        import tempfile
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for name in ['build-versions.json', 'pgbuild/Makefile', 'pyproject.toml', 'README.md']:
                target = root / name
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(ROOT / name, target)
            (root / 'src/pgserver').mkdir(parents=True)
            config = json.loads((root / 'build-versions.json').read_text())
            minor = int(config['postgres']['18']['version'].split('.')[1]) + 1
            entry = config['postgres']['18']
            entry.update(version=f'18.{minor}', package_version=f'18.{minor}.0', sha256='b' * 64, release_tag=f'pg18.{minor}-pgv0.8.6')
            updater.save_config(root, config)
            self.assertIn(f'POSTGRES_VERSION ?= 18.{minor}', (root / 'pgbuild/Makefile').read_text())
            self.assertIn('POSTGRES_SHA256 ?= ' + 'b' * 64, (root / 'pgbuild/Makefile').read_text())
            self.assertIn(f'version = "18.{minor}.0"', (root / 'pyproject.toml').read_text())
            info = json.loads((root / 'src/pgserver/_build_info.json').read_text())
            self.assertEqual(info['version'], f'18.{minor}')
            self.assertIn(f'| 18.{minor} |', (root / 'README.md').read_text())

class PublicationRetries(unittest.TestCase):
    def run_publisher(self, releases, ref_exists=True):
        import contextlib
        import os
        import runpy
        import tempfile
        from unittest.mock import patch
        config = json.loads((ROOT / 'build-versions.json').read_text())
        entry = config['postgres']['18']
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'build-versions.json').write_text(json.dumps(config))
            (root / 'dist').mkdir()
            for name in expected_wheels(entry) | {'SHA256SUMS'}:
                (root / 'dist' / name).write_text('test artifact')
            with contextlib.chdir(root), patch.dict(os.environ, PG_MAJOR='18', GITHUB_REPOSITORY='DocumentDrivenDX/pgserver', SOURCE_SHA='c' * 40), patch('release_status.get_release', side_effect=releases), patch('release_status.get_ref', return_value={'object': {}} if ref_exists else None), patch('subprocess.run') as command:
                try:
                    runpy.run_path(str(ROOT / 'scripts/publish-release.py'))
                except SystemExit as result:
                    if result.code != 0:
                        raise
                return [call.args[0] for call in command.call_args_list]

    def fixture(self, draft=False):
        entry = json.loads((ROOT / 'build-versions.json').read_text())['postgres']['18']
        return {'draft': draft, 'prerelease': False, 'assets': [{'name': name, 'state': 'uploaded', 'size': 10} for name in expected_wheels(entry) | {'SHA256SUMS'}]}

    def test_published_release_is_never_overwritten(self):
        self.assertEqual(self.run_publisher([self.fixture()]), [])

    def test_draft_retry_updates_only_unpublished_tag_and_finishes_upload(self):
        commands = self.run_publisher([self.fixture(draft=True), self.fixture(draft=True)])
        self.assertEqual(commands[0][:2], ['gh', 'api'])
        self.assertIn('force=true', commands[0])
        self.assertEqual(commands[1][:3], ['gh', 'release', 'upload'])
        self.assertEqual(commands[2][:3], ['gh', 'release', 'edit'])
        self.assertIn('--draft=false', commands[2])

    def test_new_release_remains_draft_until_all_assets_are_uploaded(self):
        commands = self.run_publisher([None, self.fixture(draft=True)])
        self.assertEqual(commands[0][:3], ['gh', 'release', 'create'])
        self.assertIn('--draft', commands[0])
        self.assertEqual(commands[-1][:3], ['gh', 'release', 'edit'])

    def test_draft_without_a_tag_can_be_retried(self):
        commands = self.run_publisher([self.fixture(draft=True), self.fixture(draft=True)], ref_exists=False)
        self.assertIn('POST', commands[0])
        self.assertIn('ref=refs/tags/pg18.6-pgv0.8.6-r1', commands[0])
        self.assertIn('--draft=false', commands[-1])
