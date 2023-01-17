# Copyright 2023 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""This file is used by various thin wrappers to find reclient binaries and
configurations at default locations in a gclient project or using
NINJA_RECLIENT_BIN_DIR and NINJA_RECLIENT_CFG environment variables"""

import os
from functools import cache

import gclient_paths


class NotFoundError(Exception):
  """A file could not be found."""

  def __init__(self, e):
    super().__init__(
        'Problem while looking for reclient in Chromium source tree:\n'
        '%s' % e)


@cache
def find_reclient_bin_dir():
  tools_path = gclient_paths.GetBuildtoolsPath()
  if not tools_path:
    raise NotFoundError(
        'Could not find checkout in any parent of the current path.\n')

  reclient_bin_dir = os.path.join(tools_path, 'reclient')
  if os.path.isdir(reclient_bin_dir):
    return reclient_bin_dir
  raise NotFoundError(
      'Could not find reclient binaries in //buildtools/reclient.\n'
      'Try running gclient sync.')


@cache
def find_reclient_cfg():
  tools_path = gclient_paths.GetBuildtoolsPath()
  if not tools_path:
    raise NotFoundError(
        'Could not find checkout in any parent of the current path.\n')

  reclient_cfg = os.path.join(tools_path, 'reclient_cfgs', 'reproxy.cfg')
  if os.path.isfile(reclient_cfg):
    return reclient_cfg
  raise NotFoundError(
      'Could not find reproxy.cfg at //buildtools/reclient_cfgs/reproxy.cfg.\n'
      'Developer builds are not currently supported, use ninja.py for now.')
