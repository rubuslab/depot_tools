#!/usr/bin/env python
# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import optparse
import os
import subprocess
import sys


# This function comes directly from src/tools/vim/ninja-build.vim in the
# Chromium repository.
def path_to_source_root(path):
  """Returns the absolute path to the chromium source root."""
  candidate = os.path.dirname(path)
  # This is a list of files that need to identify the src directory. The shorter
  # it is, the more likely it's wrong (checking for just "build/common.gypi"
  # would find "src/v8" for files below "src/v8", as "src/v8/build/common.gypi"
  # exists). The longer it is, the more likely it is to break when we rename
  # directories.
  fingerprints = ['chrome', 'net', 'v8', 'build', 'skia']
  while candidate and not all(
      [os.path.isdir(os.path.join(candidate, fp)) for fp in fingerprints]):
    candidate = os.path.dirname(candidate)
  return candidate


def main():
  parser = optparse.OptionParser(usage='%prog [options]')
  parser.add_option('--file-path', help='The file path, could be absolute or '
                    'relative to the current directory.')
  parser.add_option('--build-dir', help='The build directory, relative to the '
                    'source directory.')

  options, _ = parser.parse_args()

  if not options.file_path:
    parser.error('--file-path is required.')
  if not options.build_dir:
    parser.error('--build-dir is required.')

  src_dir = path_to_source_root(options.file_path)
  src_relpath = os.path.relpath(os.path.abspath(options.file_path),
                                os.path.join(src_dir,
                                             os.path.relpath(options.build_dir,
                                                             src_dir)))

  print 'Building %s' % options.file_path

  ninja_exec = 'ninja'
  carets = '^'
  # We need to make sure that we call the ninja executable, calling directly
  # |ninja| might end up calling a wrapper script that'll remove the caret
  # characters.
  if sys.platform.startswith('win'):
    ninja_exec = 'ninja.exe'
    # The caret character has to be escaped on Windows as it's an escape
    # character.
    carets = '^^'

  command = [
      ninja_exec,
      '-C', os.path.abspath(options.build_dir),
      '%s%s' % (src_relpath, carets)
  ]
  proc = subprocess.Popen(command, stdout=subprocess.PIPE,
                          shell=sys.platform.startswith('win'),
                          stderr=subprocess.STDOUT, stdin=subprocess.PIPE)
  print proc.communicate()[0]


if __name__ == '__main__':
  sys.exit(main())
