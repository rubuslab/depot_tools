#!/usr/bin/env python3
# Copyright 2023 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""This script manages the counter for how many times developers should
be notified before uploading reclient metrics."""

import json
import os
import subprocess
import sys

THIS_DIR = os.path.dirname(__file__)
CONFIG = os.path.join(THIS_DIR, 'reclient_metrics.cfg')
VERSION = 1


def load_config():
  if os.path.isfile(CONFIG):
    with open(CONFIG, 'r') as f:
      try:
        config = json.load(f)
      except Exception:
        # Set default value when failed to load config.
        config = {
            'is-googler': is_googler(),
            'countdown': 10,
            'version': VERSION,
        }

      if config['version'] == VERSION:
        config['countdown'] = max(0, config['countdown'] - 1)
        return config

  return {
      'is-googler': is_googler(),
      'countdown': 10,
      'version': VERSION,
  }


def save_config(config):
  with open(CONFIG, 'w') as f:
    json.dump(config, f)


def show_message(config, ninja_out):
  countdown = config.get("countdown", 0)
  if countdown <= 0 or not eligible_for_metrics(config):
    return
  print("""
Your reclient metrics will be uploaded to the chromium build metrics database. The uploaded metrics will be used to analyze user side build performance.

We upload the contents of %s/.reproxy_tmp/logs/rbe_metrics.txt.
This contains
* Flags passed to reproxy
  * Auth related flags are filtered out by reproxy
* Start and end time of build tasks
* Aggregated durations and counts of events during remote build actions
* OS (e.g. Win, Mac or Linux)
* Number of cpu cores and the amount of RAM of the building machine

Uploading reclient metrics will be started after you run autoninja another %d time(s).

If you don't want to upload reclient metrics, please run following command.
$ python3 %s opt-out

If you want to allow upload reclient metrics from next autoninja run, please run the
following command.
$ python3 %s opt-in

If you have questions about this, please send an email to foundry-x@google.com

You can find a more detailed explanation in
%s
or
https://chromium.googlesource.com/chromium/tools/depot_tools/+/main/reclient_metrics.README.md
""" % (
      ninja_out,
      countdown,
      __file__,
      __file__,
      os.path.abspath(os.path.join(THIS_DIR, "reclient_metrics.README.md")),
  ))
  save_config(config)


def eligible_for_metrics(config):
  return is_googler(config) and ('opt-in' not in config or config['opt-in'])


def is_googler(config=None):
  """Check whether this user is Googler or not."""
  if config is not None and 'is-googler' in config:
    return config['is-googler']
  p = subprocess.run('luci-auth info',
                     stdout=subprocess.PIPE,
                     stderr=subprocess.PIPE,
                     universal_newlines=True,
                     shell=True)
  if p.returncode != 0:
    return False
  lines = p.stdout.splitlines()
  if len(lines) == 0:
    return False
  l = lines[0]
  # |l| will be like 'Logged in as <user>@google.com.' for googlers.
  return l.startswith('Logged in as ') and l.endswith('@google.com.')


def should_collect_metrics(config):
  if not eligible_for_metrics(config):
    return False
  if config.get("countdown", 0) > 0:
    return False
  return True


def main(argv):
  metrics_config = load_config()

  if not is_googler(metrics_config):
    return 0

  if len(argv) == 2 and argv[1] == 'opt-in':
    metrics_config['opt-in'] = True
    metrics_config['countdown'] = 0
    save_config(metrics_config)
    print('reclient metrics upload is opted in.')
    return 0

  if len(argv) == 2 and argv[1] == 'opt-out':
    metrics_config['opt-in'] = False
    save_config(metrics_config)
    print('reclient metrics upload is opted out.')
    return 0


if __name__ == '__main__':
  sys.exit(main(sys.argv))
