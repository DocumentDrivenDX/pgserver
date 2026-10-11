"""Verify the installed wheel, rather than a source-tree build."""
from importlib.metadata import version
from pathlib import Path
import subprocess
import pgserver
from pgserver._commands import POSTGRES_BIN_PATH


def test_release_contents():
    assert version('pgserver-pg18') == '18.6.0'
    output = subprocess.check_output([str(POSTGRES_BIN_PATH / 'postgres'), '--version'], text=True)
    assert output.strip() == 'postgres (PostgreSQL) 18.6'
    licenses = Path(pgserver.__file__).parent / 'licenses'
    for name in ['PostgreSQL.txt', 'pgvector.txt']:
        assert 'Permission to use, copy, modify' in (licenses / name).read_text()


def test_release_runtime(tmp_path):
    with pgserver.get_server(tmp_path / 'data') as server:
        result = server.psql("SELECT current_setting('server_version_num'); CREATE EXTENSION vector; SELECT extversion FROM pg_extension WHERE extname = 'vector'; SHOW listen_addresses;")
        assert '180006' in result
        assert '0.8.6' in result
        assert server.get_postmaster_info().socket_dir is not None
        assert server.get_postmaster_info().hostname is None
    assert not server.get_postmaster_info().is_running()
