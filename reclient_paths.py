# Copyright 2023 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""This file is used by various thin wrappers to find reclient binaries and
configurations at default locations in a gclient project or using
NINJA_RECLIENT_BIN_DIR and NINJA_RECLIENT_CFG environment variables"""

import os

import gclient_paths

BIN_DIR_ENV_KEY = "NINJA_RECLIENT_BIN_DIR"
CFG_ENV_KEY = "NINJA_RECLIENT_CFG"


def find_reclient_bin_dir():
  # Try to find reclient binaries by environment variable
  if os.environ.get(BIN_DIR_ENV_KEY) is not None and os.path.isdir(
      os.environ[BIN_DIR_ENV_KEY]):
    return os.environ[BIN_DIR_ENV_KEY]

  # Get gclient root + src.
  primary_solution_path = gclient_paths.GetPrimarySolutionPath()
  gclient_root_path = gclient_paths.FindGclientRoot(os.getcwd())
  for base_path in [primary_solution_path, gclient_root_path]:
    if not base_path:
      continue
    reclient_bin_dir = os.path.join(base_path, 'buildtools', 'reclient')
    if os.path.isdir(reclient_bin_dir):
      os.environ[BIN_DIR_ENV_KEY] = reclient_bin_dir
      return reclient_bin_dir


def find_reclient_cfg():
  # Try to find reproxy.cfg by environment variable
  if os.environ.get(CFG_ENV_KEY) is not None and os.path.isfile(
      os.environ[CFG_ENV_KEY]):
    return os.environ[CFG_ENV_KEY]

  # Get gclient root + src.
  primary_solution_path = gclient_paths.GetPrimarySolutionPath()
  gclient_root_path = gclient_paths.FindGclientRoot(os.getcwd())
  for base_path in [primary_solution_path, gclient_root_path]:
    if not base_path:
      continue
    reclient_cfg = os.path.join(base_path, 'buildtools', 'reclient_cfgs',
                                'reproxy.cfg')
    if os.path.isfile(reclient_cfg):
      os.environ[CFG_ENV_KEY] = reclient_cfg
      return reclient_cfg
