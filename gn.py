#!/usr/bin/env python
# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""This script is a wrapper around the GN binary that is pulled from Google
Cloud Storage when you sync Chrome. The binaries go into platform-specific
subdirectories in the source tree.

This script makes there be one place for forwarding to the correct platform's
binary. It will also automatically try to find the gn binary when run inside
the chrome source tree, so users can just type "gn" on the command line
(normally depot_tools is on the path)."""

import gclient_utils
import os
import subprocess
import sys

# Pass this argument to build GN from source and use it.
_BUILD_GN_ARG = '--build-gn'


def _must_be_checkout():
  print >> sys.stderr, ('gn.py: Could not find checkout in '
                        'any parent of the current path.\n'
                        'This must be run inside a checkout.')


def _exe_not_found(exe, path):
  print >> sys.stderr, 'gn.py: Could not find %s executable at: %s' % exe, path


def _call(cmd, cwd):
  proc = subprocess.Popen(cmd, cwd=cwd,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE)
  out, err = proc.communicate()
  return proc.returncode, out or '', err or ''


def find_golden_gn():
  bin_path = gclient_utils.GetBuildtoolsPlatformBinaryPath()
  if not bin_path:
    _must_be_checkout()
    return None

  gn_path = os.path.join(bin_path, 'gn' + gclient_utils.GetExeSuffix())
  if not os.path.exists(gn_path):
    _exe_not_found('gn', gn_path)
    return None
  return gn_path


def build_gn():
  print 'Building GN from //tools/gn...'
  src_path = gclient_utils.GetPrimarySolutionPath()
  if not src_path:
    _must_be_checkout()
    return None
  gn_out_path = os.path.join(src_path, 'out', 'gn_latest_build')

  golden_gn_path = find_golden_gn()
  if not golden_gn_path:
    return None

  # No need to call GN manually if ninja output is already generated.
  if not os.path.exists(gn_out_path):
    build_init_run = _call([golden_gn_path, 'gen',
                           '--args=is_debug=false', gn_out_path], cwd=src_path)
    if build_init_run[0] != 0:
      print >> sys.stderr, build_init_run[1].strip()
      print >> sys.stderr, build_init_run[2].strip()
      print >> sys.stderr, 'gn.py: Could not initialize GN build.'
      return None

  self_path = os.path.dirname(os.path.realpath(__file__))
  ninja_path = os.path.join(self_path, 'ninja' + gclient_utils.GetExeSuffix())
  if not os.path.exists(ninja_path):
    _exe_not_found('ninja', ninja_path)
    return None

  build_run = _call([ninja_path, 'gn'], cwd=gn_out_path)
  if build_run[0] != 0:
    print >> sys.stderr, build_run[1].strip()
    print >> sys.stderr, build_run[2].strip()
    print >> sys.stderr, 'gn.py: Could not build GN from the current checkout.'
    return None

  if build_run[1].startswith('ninja: no work to do'):
    print 'Already up to date.'
  else:
    print 'Done.'

  new_gn_path = os.path.join(gn_out_path, 'gn' + gclient_utils.GetExeSuffix())
  if not os.path.exists(new_gn_path):
    _exe_not_found('newly built gn', new_gn_path)
    return None
  return new_gn_path


def main(args):
  if _BUILD_GN_ARG in args:
    args = filter(lambda arg: arg != _BUILD_GN_ARG, args)
    gn_path = build_gn()
  else:
    gn_path = find_golden_gn()

  if not gn_path:
    return 1
  return subprocess.call([gn_path] + args[1:])


if __name__ == '__main__':
  try:
    sys.exit(main(sys.argv))
  except KeyboardInterrupt:
    sys.stderr.write('interrupted\n')
    sys.exit(1)
