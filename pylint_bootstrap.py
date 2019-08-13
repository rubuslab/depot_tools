#!/usr/bin/env python
# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""A wrapper script for selecting different pylint versions via vpython."""

from __future__ import print_function

import argparse
import os
import subprocess
import sys


HERE = os.path.dirname(os.path.abspath(__file__))
PYLINT = os.path.join(HERE, 'pylint_main.py')
RC_FILE = os.path.join(HERE, 'pylintrc')

THIRD_PARTY_DIR = os.path.join(HERE, 'third_party')
PYLINT_DEPS_DIR = os.path.join(THIRD_PARTY_DIR, 'logilab')


def get_parser():
  """Get a custom CLI parser with our extensions."""
  parser = argparse.ArgumentParser(description=__doc__, add_help=False)
  # Manage the --help flag ourselves to show our help & pylint's help.
  parser.add_argument('-h', '--help', action='store_true',
                      help='Show help information')
  parser.add_argument('--pylint-version', choices=('1.5', '1.8'),
                      default='1.5',
                      help='Run a specific version of pylint '
                           '(default: %(default)s)')
  return parser


def main(argv):
  """Our main wrapper."""
  parser = get_parser()
  opts, args = parser.parse_known_args(argv)

  if opts.help:
    parser.print_help()
    args.insert(0, '--help')

  # Figure out which version to run.
  if opts.pylint_version == '1.5':
    # This is the version bundled in depot_tools.
    # TODO(crbug.com/866772): Move this to cipd+vpython.
    pypath = os.environ.get('PYTHONPATH', '').split(os.pathsep)
    # Add local modules to the search path.
    pypath.insert(0, PYLINT_DEPS_DIR)
    pypath.insert(0, THIRD_PARTY_DIR)
    os.environ['PYTHONPATH'] = os.pathsep.join(pypath)
    command = []
  else:
    vpython_spec = os.path.join(
        HERE, 'pylint-%s.vpython' % (opts.pylint_version,))
    command = [
        'vpython',
        '-vpython-spec', vpython_spec,
        '--',
    ]
  command.append(PYLINT)

  # We prepend the command-line with the depot_tools rcfile. If another rcfile
  # is to be used, passing --rcfile a second time on the command-line will work
  # fine.
  if os.path.isfile(RC_FILE):
    # The file can be removed to test 'normal' pylint behavior.
    command.append('--rcfile=%s' % RC_FILE)

  # Add the user args.
  command.extend(args)
  try:
    sys.exit(subprocess.call(command))
  except KeyboardInterrupt:
    sys.stderr.write('interrupted\n')
    sys.exit(1)


if __name__ == '__main__':
  sys.exit(main(sys.argv[1:]))
