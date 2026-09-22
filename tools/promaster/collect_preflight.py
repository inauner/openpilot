#!/usr/bin/env python3
"""Print a read-only setup report for ProMaster development.

Run with the Python environment used by the ACTIVE openpilot installation.
This script never opens panda, publishes messages, changes params, or flashes.
It omits VIN, dongle ID, Git remote URLs, SSH keys, and account tokens.
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path


def git(path, *args):
  try:
    result = subprocess.run(['git', '-C', str(path), *args], capture_output=True, text=True, timeout=15, check=False)
    return result.stdout.strip() if result.returncode == 0 else 'unavailable'
  except (OSError, subprocess.TimeoutExpired):
    return 'unavailable'


def checkout(path):
  return {
    'commit': git(path, 'rev-parse', 'HEAD'),
    'branch': git(path, 'branch', '--show-current'),
    'changes': git(path, 'status', '--short'),
    'prebuilt_present': (path / 'prebuilt').exists(),
    'opendbc_commit': git(path / 'opendbc_repo', 'rev-parse', 'HEAD') if (path / 'opendbc_repo/.git').exists() else 'unavailable',
    'panda_commit': git(path / 'panda', 'rev-parse', 'HEAD') if (path / 'panda/.git').exists() else 'unavailable',
  }


def car_params(active, params):
  # Import only the active checkout's schema. Cached params may belong to another vehicle.
  sys.path.insert(0, str(active))
  try:
    from cereal import car
  except ImportError:
    return {'unavailable': 'Run with the active installation Python environment (cereal/pycapnp required).'}

  result = {}
  for name in ('CarParams', 'CarParamsCache', 'CarParamsPersistent'):
    path = params / name
    if not path.is_file():
      continue
    try:
      with car.CarParams.from_bytes(path.read_bytes()) as cp:
        data = cp.to_dict()
        result[name] = {key: data.get(key) for key in (
          'carFingerprint', 'brand', 'carName', 'dashcamOnly', 'passive',
          'safetyConfigs', 'minSteerSpeed', 'openpilotLongitudinalControl',
        )}
        result[name]['file_mtime_unix'] = path.stat().st_mtime
        result[name]['eps_firmware'] = [
          {'address': hex(fw['address']), 'firmware_hex': fw['fwVersion'].hex()}
          for fw in data.get('carFw', []) if str(fw.get('ecu')) == 'eps'
        ]
    except Exception as exc:  # Schema incompatibility must not prevent returning the rest of the preflight.
      result[name] = {'unavailable': type(exc).__name__}
  return result or {'unavailable': 'No saved CarParams found; share a full route log.'}


def main():
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument('--active', type=Path, default=Path('/data/openpilot'))
  parser.add_argument('--params', type=Path, default=Path('/data/params/d'))
  args = parser.parse_args()
  version = Path('/VERSION')
  report = {
    'agnos_version': version.read_text().strip() if version.is_file() else 'unavailable',
    'python_version': sys.version.split()[0],
    'active_checkout': checkout(args.active),
    'saved_car_params': car_params(args.active, args.params),
    'note': 'Saved params may be stale. This report does not verify running panda firmware or authorize an actuation test.',
  }
  print(json.dumps(report, indent=2))


if __name__ == '__main__':
  main()
