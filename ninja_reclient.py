#!/usr/bin/env python3
# Copyright 2022 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""This script is a wrapper around the ninja.py script that also handles the
client lifecycle safely. It will automatically start reproxy before running ninja
and stop reproxy when ninja stops for any reason eg. build completes, keyboard interupt etc."""

import argparse
import subprocess
import sys
import os

import reclient_paths
import ninja


def run(cmd_args):
  print(' '.join(cmd_args))
  subprocess.call(cmd_args)


def start_reproxy(reclient_cfg, reclient_bin_dir):
  run([
      os.path.join(reclient_bin_dir, 'bootstrap'), '--cfg=' + reclient_cfg,
      '--re_proxy=' + os.path.join(reclient_bin_dir, 'reproxy')
  ])


def stop_reproxy(reclient_cfg, reclient_bin_dir):
  run([
      os.path.join(reclient_bin_dir, 'bootstrap'),
      '--cfg=' + reclient_cfg,
      '--shutdown',
  ])


if __name__ == '__main__':
  reclient_bin_dir = reclient_paths.find_reclient_bin_dir()
  reclient_cfg = reclient_paths.find_reclient_cfg()
  if reclient_bin_dir is None:
    print("Reclient binaries not found.")
    sys.exit(1)
  if reclient_cfg is None:
    print("reproxy.cfg not found.")
    sys.exit(1)
  try:
    start_reproxy(reclient_cfg, reclient_bin_dir)
    sys.exit(ninja.main(sys.argv))
  except KeyboardInterrupt:
    stop_reproxy(reclient_cfg, reclient_bin_dir)
    sys.exit(1)
