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


class PendingReleases(unittest.TestCase):
    def test_versions_missing_from_pypi_are_pending(self):
        import io
        import urllib.error

        def fake_fetch(url):
            if '/pgserver-pg17/' in url:
                return io.BytesIO(b'{}')
            raise urllib.error.HTTPError(url, 404, 'Not Found', {}, None)
        with patch.object(updater, 'fetch', side_effect=fake_fetch):
            self.assertEqual(updater.pending_majors(self.config()), ['16', '18'])

    def test_other_http_errors_are_not_treated_as_missing(self):
        import urllib.error
        with patch.object(updater, 'fetch', side_effect=urllib.error.HTTPError('u', 503, 'down', {}, None)):
            with self.assertRaises(urllib.error.HTTPError):
                updater.pending_majors(self.config())

    def config(self):
        return json.loads((ROOT / 'build-versions.json').read_text())


if __name__ == '__main__':
    unittest.main()
