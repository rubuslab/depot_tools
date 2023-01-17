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


class NotFoundError(Exception):
  """A file could not be found."""

  def __init__(self, e):
    super().__init__(
        'Problem while looking for reclient in Chromium source tree:\n'
        '%s' % e)


def find_reclient_bin_dir():
  # Try to find reclient binaries by environment variable
  if os.environ.get(BIN_DIR_ENV_KEY) is not None:
    reclient_bin_dir = os.environ.get(BIN_DIR_ENV_KEY)
    if os.path.isdir(reclient_bin_dir):
      return reclient_bin_dir
    raise NotFoundError(
        'Could not find reclient binaries at %s specified by the %s '
        'environment variable' % (reclient_bin_dir, BIN_DIR_ENV_KEY))

  tools_path = gclient_paths.GetBuildtoolsPath()
  if not tools_path:
    raise NotFoundError(
        'Could not find checkout in any parent of the current path.\n'
        'Set NINJA_RECLIENT_BIN_DIR to use outside of a chromium checkout.')

  reclient_bin_dir = os.path.join(tools_path, 'reclient')
  if os.path.isdir(reclient_bin_dir):
    os.environ[BIN_DIR_ENV_KEY] = reclient_bin_dir
    return reclient_bin_dir
  raise NotFoundError(
      'Could not find reclient binaries in //buildtools/reclient.\n'
      'Try running gclient sync.')


def find_reclient_cfg():
  # Try to find reproxy.cfg by environment variable
  if os.environ.get(CFG_ENV_KEY) is not None:
    reclient_cfg = os.environ.get(CFG_ENV_KEY)
    if os.path.isfile(reclient_cfg):
      return reclient_cfg
    raise NotFoundError(
        'Could not find reclient reproxy.cfg at %s specified by the %s '
        'environment variable' % (reclient_cfg, CFG_ENV_KEY))

  tools_path = gclient_paths.GetBuildtoolsPath()
  if not tools_path:
    raise NotFoundError(
        'Could not find checkout in any parent of the current path.\n'
        'Set NINJA_RECLIENT_CFG to use outside of a chromium checkout.')

  reclient_cfg = os.path.join(tools_path, 'reclient_cfgs', 'reproxy.cfg')
  if os.path.isfile(reclient_cfg):
    os.environ[CFG_ENV_KEY] = reclient_cfg
    return reclient_cfg
  raise NotFoundError(
      'Could not find reproxy.cfg at //buildtools/reclient_cfgs/reproxy.cfg.\n'
      'Developer builds are not currently supported, use ninja.py for now.')
