#!/usr/bin/env python3
# Copyright 2023 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""This script is a wrapper around the ninja.py script that also 
handles the client lifecycle safely. It will automatically start 
reproxy before running ninja and stop reproxy when ninja stops 
for any reason eg. build completes, keyboard interupt etc."""

import os
import subprocess
import sys

import ninja
import reclient_paths


def run(cmd_args):
  if os.environ.get('NINJA_SUMMARIZE_BUILD', '0') == '1':
    print(' '.join(cmd_args))
  return subprocess.call(cmd_args)


def start_reproxy(reclient_cfg, reclient_bin_dir):
  cmd = [
      os.path.join(reclient_bin_dir, 'bootstrap'),
      '--re_proxy=' + os.path.join(reclient_bin_dir, 'reproxy')
  ]
  if reclient_cfg is not None:
    cmd.append('--cfg=' + reclient_cfg)
  return run(cmd)


def stop_reproxy(reclient_cfg, reclient_bin_dir):
  cmd = [
      os.path.join(reclient_bin_dir, 'bootstrap'),
      '--shutdown',
  ]
  if reclient_cfg is not None:
    cmd.append('--cfg=' + reclient_cfg)
  return run(cmd)


def main(argv):
  reclient_bin_dir = reclient_paths.find_reclient_bin_dir()
  reclient_cfg = reclient_paths.find_reclient_cfg()
  if reclient_bin_dir is None:
    print("Reclient binaries not found.")
    return 1
  reproxy_ret_code = start_reproxy(reclient_cfg, reclient_bin_dir)
  if reproxy_ret_code != 0:
    return reproxy_ret_code
  try:
    return ninja.main(argv)
  except KeyboardInterrupt:
    return 1
  finally:
    stop_reproxy(reclient_cfg, reclient_bin_dir)


if __name__ == '__main__':
  sys.exit(main(sys.argv))
