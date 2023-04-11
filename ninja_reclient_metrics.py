#!/usr/bin/env python3
# Copyright 2023 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""This script manages the counter for how many times developers should
be notified before uploading reclient metrics."""

import json
import os
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
            'countdown': 10,
            'version': VERSION,
        }

      if config['version'] == VERSION:
        config['countdown'] = max(0, config['countdown'] - 1)
        return config

  return {
      'countdown': 10,
      'version': VERSION,
  }


def save_config(config):
  with open(CONFIG, 'w') as f:
    json.dump(config, f)


def show_message(config):
  countdown = config.get("countdown", 0)
  if countdown <= 0:
    return
  print("""
Your reclient metrics will be uploaded to the chromium build metrics database. The uploaded metrics will be used to analyze user side build performance.

The contents of rbe_metrics.txt in the .reproxy_tmp/logs directory in your ninja out directory
This contains
* Flags passed to reproxy
  * Auth related flags are filtered out by reproxy
* start and end time of build tasks
* Aggregated durations and counts of events during remote build actions
* OS (e.g. Win, Mac or Linux)
* number of cpu cores of building machine

Uploading reclient metrics will be started after you run autoninja another %d time(s).

If you don't want to upload reclient metrics, please run following command.
$ python3 %s opt-out

If you want to allow upload reclient metrics from next autoninja run, please run the
following command.
$ python3 %s opt-in

If you have questions about this, please send mail to infra-dev@chromium.org

You can find a more detailed explanation in
//buildtools/reclient_cfgs/rbe_metrics.README.md
or
https://source.chromium.org/chromium/chromium/src/+/main:buildtools/reclient_cfgs/rbe_metrics.README.md
""" % (countdown, __file__, __file__))
  save_config(config)


def should_collect_metrics(config):
  if 'opt-in' in config and not config['opt-in']:
    # Upload is opted out.
    return False
  if config.get("countdown", 0) > 0:
    return False
  return True


def main(argv):
  metrics_config = load_config()

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
