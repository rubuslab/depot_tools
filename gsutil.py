#!/usr/bin/env python3
# Copyright 2022 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Run gsutil shim from CIPD gcloud binary."""


import argparse
import os
import subprocess
import sys

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
IS_WINDOWS = os.name == 'nt'

CIPD_COMMAND = os.path.join(THIS_DIR, 'cipd.bat' if IS_WINDOWS else 'cipd')
CIPD_MANIFEST = os.path.join(THIS_DIR, 'cipd_manifest.txt')
CIPD_BIN = os.path.join(THIS_DIR, '.cipd_bin')
GSUTIL_SHIM_PATH = os.path.join(CIPD_BIN, 'bin', 'gsutil')


def cipd_bin_setup():
  """Sets up CIPD bin."""
  if not (os.path.exists(CIPD_BIN) and os.path.exists(GSUTIL_SHIM_PATH)):
    # TODO(aravindvasudev): Add cygwin support.
    cmd = [
        CIPD_COMMAND, 'ensure', '-log-level', 'warning', '-ensure-file',
        CIPD_MANIFEST, '-root', CIPD_BIN
    ]
    subprocess.call(cmd, shell=IS_WINDOWS)


def ensure_gsutil():
  cipd_bin_setup()

  assert os.path.exists(GSUTIL_SHIM_PATH)
  return GSUTIL_SHIM_PATH


def run_gsutil(args):
  gsutil_bin = ensure_gsutil()
  args_opt = ['-o', 'GSUtil:software_update_check_period=0']

  if sys.platform == 'darwin':
    # We are experiencing problems with multiprocessing on MacOS where gsutil.py
    # may hang.
    # This behavior is documented in gsutil codebase, and recommendation is to
    # set GSUtil:parallel_process_count=1.
    # https://github.com/GoogleCloudPlatform/gsutil/blob/06efc9dc23719fab4fd5fadb506d252bbd3fe0dd/gslib/command.py#L1331
    # https://github.com/GoogleCloudPlatform/gsutil/issues/1100
    args_opt.extend(['-o', 'GSUtil:parallel_process_count=1'])

  cmd = [gsutil_bin] + args_opt + args
  return subprocess.call(cmd, shell=IS_WINDOWS)


def parse_args():
  # Help is disabled as it conflicts with gsutil -h, which controls headers.
  parser = argparse.ArgumentParser(add_help=False)

  # These four args exist for backwards-compatibility but are no-ops.
  parser.add_argument('--clean',
                      action='store_true',
                      help='(deprecated, this flag has no effect)')
  parser.add_argument(
      '--target',
      default=CIPD_BIN,
      help='The target directory to download/store a gsutil version in. '
      '(deprecated, this flag has no effect)')
  parser.add_argument('--force-version',
                      help='(deprecated, this flag has no effect)')
  parser.add_argument('--fallback',
                      help='(deprecated, this flag has no effect)')

  parser.add_argument('args', nargs=argparse.REMAINDER)

  args, extras = parser.parse_known_args()
  if args.args and args.args[0] == '--':
    args.args.pop(0)
  if extras:
    args.args = extras + args.args
  return args


def main():
  args = parse_args()
  return run_gsutil(args.args)


if __name__ == '__main__':
  sys.exit(main())
