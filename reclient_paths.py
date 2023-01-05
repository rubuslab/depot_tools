# Copyright 2023 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""This file is used by various thin wrappers to find reclient binaries and configurations
at default locations in a gclient project"""


import os

import gclient_paths

def find_reclient_bin_dir():
  # Get gclient root + src.
  primary_solution_path = gclient_paths.GetPrimarySolutionPath()
  gclient_root_path = gclient_paths.FindGclientRoot(os.getcwd())
  for base_path in [primary_solution_path, gclient_root_path]:
    if not base_path:
      continue
    reclient_bin_dir = os.path.join(base_path, 'buildtools', 'reclient')
    if os.path.isdir(reclient_bin_dir):
      return reclient_bin_dir

def find_reclient_cfg():
  # Get gclient root + src.
  primary_solution_path = gclient_paths.GetPrimarySolutionPath()
  gclient_root_path = gclient_paths.FindGclientRoot(os.getcwd())
  for base_path in [primary_solution_path, gclient_root_path]:
    if not base_path:
      continue
    reclient_cfg = os.path.join(base_path, 'buildtools', 'reclient_cfgs','reproxy.cfg')
    if os.path.isfile(reclient_cfg):
      return reclient_cfg