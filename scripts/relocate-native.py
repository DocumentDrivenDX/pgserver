"""Remove build-prefix loader paths before packaging native executables/libraries."""
from pathlib import Path
import os
import platform
import subprocess

root = Path(__file__).resolve().parents[1] / 'src/pgserver/pginstall'
files = [p for area in ['bin', 'lib'] for p in (root / area).rglob('*') if p.is_file() and not p.is_symlink()]
for path in files:
    magic = path.read_bytes()[:4]
    if platform.system() == 'Darwin' and magic in [b'\xcf\xfa\xed\xfe', b'\xfe\xed\xfa\xcf', b'\xca\xfe\xba\xbe']:
        dependencies = subprocess.check_output(['otool', '-L', str(path)], text=True).splitlines()[1:]
        if path.suffix == '.dylib':
            subprocess.run(['install_name_tool', '-id', '@rpath/' + path.name, str(path)], check=True)
        for line in dependencies:
            dependency = line.strip().split(' (')[0]
            if '/pginstall/lib/' in dependency:
                target = root / 'lib' / Path(dependency).name
                if not target.exists():
                    raise SystemExit(f'Missing bundled dependency: {dependency}')
                relative = os.path.relpath(target, path.parent)
                subprocess.run(['install_name_tool', '-change', dependency, '@loader_path/' + relative, str(path)], check=True)
        subprocess.run(['codesign', '--force', '--sign', '-', str(path)], check=True)
    elif platform.system() == 'Linux' and magic == b'\x7fELF':
        # Keep PostgreSQL's bundled libpq available after installation to another prefix.
        relative = os.path.relpath(root / 'lib', path.parent)
        rpath = '$ORIGIN' if relative == '.' else '$ORIGIN/' + relative
        subprocess.run(['patchelf', '--set-rpath', rpath, str(path)], check=True)
