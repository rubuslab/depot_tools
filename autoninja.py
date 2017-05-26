# Copyright (c) 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""
This script (intended to be invoked by autoninja.bat) detects whether a build
is using goma. If so it runs with a large -j value, and otherwise it chooses a
small one. This auto-adjustment makes using goma simpler and safer, and avoids
errors that can cause slow goma builds or swap-storms on non-goma builds.
"""

import os
import multiprocessing
import re
import sys

j_specified = False
output_dir = '.'
for index, arg in enumerate(sys.argv[1:]):
  # If the -j or -C commands are specified as -j=100 or -C=out\Default then
  # autoninja.bat somehow removes the '=' sign so that this syntax doesn't
  # need to be handled (no need for optparse).
  if arg == '-j':
    j_specified = True
  if arg == '-C':
    # + 1 to get the next argument and +1 because we trimmed off sys.argv[0]
    output_dir = sys.argv[index + 2]

use_goma = False
try:
  with open(os.path.join(output_dir, 'args.gn')) as file_handle:
    for line in file_handle:
      # This regex pattern copied from create_installer_archive.py
      m = re.match('^\s*use_goma\s*=\s*true(\s*$|\s*#.*$)', line)
      if m:
        use_goma = True
except IOError:
  pass

if sys.platform.startswith('win'):
  # Specify ninja.exe on Windows so that ninja.bat can call autoninja and not
  # be called back.
  args = ['ninja.exe'] + sys.argv[1:]
else:
  args = ['ninja'] + sys.argv[1:]

num_cores = multiprocessing.cpu_count()
if not j_specified:
  if use_goma:
    args.append('-j')
    args.append('%d' % (num_cores * 20))
  else:
    # I like to run ninja at slightly less than the number of hyperthreads that
    # I have, in order to ensure system responsiveness. Due to the nature of
    # hyperthreading this should not actually slow build times.
    args.append('-j')
    args.append('%d' % (num_cores - 2))

# Specify a maximum CPU load so that running builds in two different command
# prompts won't overload the system too much. This is not reliable enough to
# be used to auto-adjust between goma/non-goma loads, but it is a nice
# fallback load balancer.
args.append('-l')
args.append('%d' % num_cores)

print ' '.join(args)

