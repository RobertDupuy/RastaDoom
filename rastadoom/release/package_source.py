#!/usr/bin/env python3
"""Package release source, binaries, licenses and functional-test evidence."""
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
import hashlib, json, shutil, subprocess

root = Path(__file__).resolve().parents[2]
out = root.parent / 'deliverables'
out.mkdir(exist_ok=True)
version = '0.6.0'
binary = root / f'dist/{version}/A8PicoCart-DOOM-{version}.uf2'
car = root / f'dist/{version}/DOOM.CAR'
checks = root / 'checks/release'
verification = json.loads((checks / 'verification.json').read_text())
assert verification['uf2_sha256'] == hashlib.sha256(binary.read_bytes()).hexdigest()
for tv in ['ntsc', 'pal']:
    result = verification[tv + '_result']
    assert result['fire_only_start'] and result['startup_text_removed']
    assert result['car_sha256'] == hashlib.sha256(car.read_bytes()).hexdigest()

shutil.copy2(binary, out / binary.name)
archive = out / f'A8PicoCart-DOOM-{version}-Source.zip'
hashes = {}
with ZipFile(archive, 'w', ZIP_DEFLATED, compresslevel=9) as z:
    def put(name, data):
        assert name not in hashes, name
        hashes[name] = hashlib.sha256(data).hexdigest()
        z.writestr(name, data)
    def add(path, name):
        put(name, path.read_bytes())
    for prefix in ['rastadoom', 'third_party', 'source', 'inputs']:
        for path in sorted((root / prefix).rglob('*')):
            if not path.is_file() or any(p in ['.git', '__pycache__'] for p in path.parts):
                continue
            add(path, path.relative_to(root).as_posix())
    add(root / 'COPYING.md', 'COPYING.md')
    add(root / 'rastadoom/release/README.txt', 'README.txt')
    add(binary, binary.name)
    add(car, car.name)
    for name in ['client-build.json', 'firmware-build.json']:
        add(root / f'dist/{version}' / name, 'checks/build/' + name)
    for path in sorted(checks.rglob('*')):
        if path.is_file() and path.name != 'server-private.log' and path.suffix in ['.json', '.jsonl', '.log', '.png']:
            add(path, path.relative_to(root).as_posix())
    put('SHA256SUMS.txt', ''.join(h + '  ' + n + '\n' for n, h in sorted(hashes.items())).encode())
with ZipFile(archive) as z:
    assert z.testzip() is None
print(json.dumps({'archive': str(archive), 'bytes': archive.stat().st_size,
                  'files': len(hashes), 'uf2_sha256': verification['uf2_sha256']}, indent=2))
