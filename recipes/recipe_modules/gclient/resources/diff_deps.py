#!/usr/bin/env python
import os
import subprocess
import sys

if '@' in os.environ.get('GCLIENT_URL'):
  ref = os.environ.get('GCLIENT_URL').split('@')[-1]
else:
  sys.exit(0)

try:
  diff = subprocess.check_output("git diff --cached --name-only %s" % ref, shell=True)
except subprocess.CalledProcessError:
  sys.exit(0)

for line in diff.split('\n'):
  if line:
    print('%s/%s' % (os.environ.get('GCLIENT_DEP_PATH', ''),  line))
