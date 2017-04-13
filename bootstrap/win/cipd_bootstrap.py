# Copyright (c) 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import os
import platform
import sys
import subprocess

THIS_DIR = os.path.abspath(os.path.dirname(__file__))
ROOT_DIR = os.path.abspath(os.path.join(THIS_DIR, '..', '..'))

cipd = {}
cipd['version'] = os.environ.get('CIPD_CLIENT_VER')
if not cipd['version']:
  cipd['version'] = open(os.path.join(ROOT_DIR, 'cipd_client_version'))\
                        .read().strip()
cipd['server'] = os.environ.get('CIPD_CLIENT_SRV',
                                'https://chrome-infra-packages.appspot.com')

cipd['plat'] = 'windows'
cipd['arch'] = '386' if platform.machine() == 'x86' else 'amd64'

cipd['url'] = '{server}/client?platform={plat}-{arch}&version={version}'\
                  .format(**cipd)
client = os.path.join(ROOT_DIR, '.cipd_client.exe')

user_agent = "depot_tools/"
try:
  depot_tools_version = subprocess.check_output(
      ['git', '-C', ROOT_DIR, 'rev-parse', 'HEAD']).strip()
except WindowsError:
  user_agent += '???'
else:
  user_agent += depot_tools_version

if not os.path.exists(client):
  print """\
Bootstrapping cipd client for {plat}-{arch}...
From {url}\
""".format(**cipd)
   
  # this download method doesn't use custom user_agent
  cmd = ['cscript', '//nologo', '//e:jscript', 'get_file.js']
  retcode = subprocess.call(cmd + [cipd['url'], client])
  if retcode != 0:
    sys.exit('error fetching cipd_client binary')


try:
  env = os.environ.copy()
  env['CIPD_HTTP_USER_AGENT_PREFIX'] = user_agent
  subprocess.call([client, 'selfupdate', '-version', cipd['version']], env=env)
except WindowsError:
  print """\
selfupdate failed: run
  set CIPD_HTTP_USER_AGENT_PREFIX={0}/manual && {1} selfupdate -version {2}
to diagnose"
""".format(user_agent, client, cipd['version'])


if not os.path.exists(client):
  sys.exit(-1)
