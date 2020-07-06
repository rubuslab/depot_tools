print('0')
import os
import subprocess
import sys

print('1')
if '@' in os.environ.get('GCLIENT_URL'):
  ref = os.environ.get('GCLIENT_URL').split('@')[-1]
  print('2')
else:
  # TODO(guterman): when the ref isn't included, we can't tell what the default branch is
  print('3')
  sys.exit(0)

try:
  diff = subprocess.check_output("git diff --cached --name-only %s" % ref, shell=True)
except subprocess.CalledProcessError:
  sys.exit(0)

for line in diff.split('\n'):
  print('%s/%s' % (os.environ.get('GCLIENT_DEP_PATH', ''),  line))
