"""Verify selected version, native contents and lifecycle from the installed wheel."""
from importlib.metadata import version
import json
from pathlib import Path
import subprocess
import pgserver
from pgserver._commands import POSTGRES_BIN_PATH

INFO = json.loads((Path(pgserver.__file__).parent / '_build_info.json').read_text())


def test_release_contents():
    assert version(INFO['distribution']) == INFO['package_version']
    output = subprocess.check_output([str(POSTGRES_BIN_PATH / 'postgres'), '--version'], text=True)
    assert output.strip() == f"postgres (PostgreSQL) {INFO['version']}"
    licenses = Path(pgserver.__file__).parent / 'licenses'
    for name in ['PostgreSQL.txt', 'pgvector.txt']:
        assert 'Permission to use, copy, modify' in (licenses / name).read_text()


def test_release_runtime(tmp_path):
    with pgserver.get_server(tmp_path / 'data') as server:
        result = server.psql("SELECT current_setting('server_version_num'); CREATE EXTENSION vector; SELECT extversion FROM pg_extension WHERE extname = 'vector';")
        major, minor = map(int, INFO['version'].split('.'))
        assert str(major * 10000 + minor) in result
        assert INFO['pgvector_version'] in result
        assert server.get_postmaster_info().socket_dir is not None
        assert server.get_postmaster_info().hostname is None
    assert not server.get_postmaster_info().is_running()


def test_short_socket_path_with_spaces_and_quotes():
    from tempfile import TemporaryDirectory
    # macOS's usual long pytest path can select a different cache socket path.
    with TemporaryDirectory(prefix="pg space ' ", dir='/tmp') as root:
        data = Path(root) / 'retained data'
        with pgserver.get_server(data) as server:
            assert server.get_postmaster_info().socket_dir == data.resolve()
            assert server.get_postmaster_info().hostname is None
            assert '42' in server.psql('SELECT 42;')
        assert not server.get_postmaster_info().is_running()
        with pgserver.get_server(data) as restarted:
            assert '42' in restarted.psql('SELECT 42;')
        assert not restarted.get_postmaster_info().is_running()
