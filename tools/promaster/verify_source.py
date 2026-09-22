#!/usr/bin/env python3
"""Read-only completeness check for the ProMaster tester checkout (Linux/AGNOS).

Run after recursive submodule initialization and git lfs pull. Does not launch
openpilot, contact panda, flash firmware, or verify physical steering behavior.
"""
import json
import subprocess
from pathlib import Path

EXPECTED_OPENDBC = 'f989636a7b9b27038c1c0faa41d07620b6b86fde'
LINKS = {
  'selfdrive/modeld/models/big_driving_policy.onnx': 'driving_policy.onnx',
  'selfdrive/modeld/models/big_driving_vision.onnx': 'driving_vision.onnx',
  'third_party/acados/Darwin/lib/libqpOASES_e.dylib': 'libqpOASES_e.3.1.dylib',
  'third_party/acados/larch64/lib/libqpOASES_e.so': 'libqpOASES_e.so.3.1',
  'third_party/acados/x86_64/lib/libqpOASES_e.so': 'libqpOASES_e.so.3.1',
}


def git(root, *args):
  return subprocess.check_output(['git', '-C', str(root), *args], text=True).strip()


def verify(root):
  errors = []
  commit = git(root, 'rev-parse', 'HEAD')
  entry = git(root, 'ls-tree', 'HEAD', 'opendbc_repo').split()
  if len(entry) < 3 or entry[2] != EXPECTED_OPENDBC:
    errors.append('The committed opendbc pin does not match this tester candidate.')
  # Do not strip leading spaces: git uses the first column for submodule state.
  status = subprocess.check_output(['git', '-C', str(root), 'submodule', 'status', '--recursive'], text=True)
  for line in status.splitlines():
    if line and line[0] != ' ':
      errors.append(f'Submodule not initialized or at the committed revision: {line}')
  if git(root, 'status', '--porcelain'):
    errors.append('Checkout has tracked changes or untracked files; inspect git status before testing.')
  if (root / 'prebuilt').exists():
    errors.append('A prebuilt marker exists; this check cannot establish which binaries will run.')
  for relative, expected in LINKS.items():
    link = root / relative
    if not link.is_symlink() or str(link.readlink()) != expected:
      errors.append(f'Expected real symlink {relative} -> {expected}')
    elif not link.is_file():
      errors.append(f'Missing symlink target: {relative}')
    else:
      with link.open('rb') as stream:
        if stream.read(100).startswith(b'version https://git-lfs.github.com/spec/v1'):
          errors.append(f'LFS content not downloaded: {relative}')
  lfs = json.loads(git(root, 'lfs', 'ls-files', '--json'))
  for item in lfs.get('files', []):
    if not item.get('checkout', False):
      errors.append(f'LFS content not checked out: {item["name"]}')
  return {'commit': commit, 'expected_opendbc': EXPECTED_OPENDBC, 'errors': errors,
          'source_complete': not errors, 'note': 'Source check only; build, running panda firmware and vehicle behavior remain separate checks.'}


if __name__ == '__main__':
  try:
    result = verify(Path(__file__).resolve().parents[2])
  except (OSError, subprocess.CalledProcessError, ValueError) as exc:
    raise SystemExit(f'Source verification could not complete: {exc}') from exc
  print(json.dumps(result, indent=2))
  raise SystemExit(0 if result['source_complete'] else 1)
