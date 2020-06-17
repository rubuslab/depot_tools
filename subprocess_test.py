import subprocess
print(subprocess.check_output(['echo "hi" | python -c "'
'''
import os
import sys
for line in sys.stdin:
  print('%s/%s' % (os.environ.get('GCLIENT_DEP_PATH'),  line))
"'''], shell=True))
