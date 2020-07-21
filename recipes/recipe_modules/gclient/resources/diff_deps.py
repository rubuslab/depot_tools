#!/usr/bin/env python
import os
import os.path
import subprocess
import sys


if '@' in os.environ.get('GCLIENT_URL'):
  ref = os.environ.get('GCLIENT_URL').split('@')[-1]
else:
  sys.exit(0)

diff = subprocess.check_output('git diff --cached --name-only %s' % ref, shell=True)

dep_path = os.environ['GCLIENT_DEP_PATH']

# Remove the first dir
dep_path = os.path.join('', *dep_path.split('/')[1:])

for line in diff.splitlines():
  if line:
    print(os.path.join(dep_path,  line))
