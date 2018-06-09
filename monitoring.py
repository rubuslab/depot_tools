#!/usr/bin/env python
# Copyright (c) 2018 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import functools
import json
import multiprocessing
import os
import subprocess
import subprocess2
import sys
import threading
import time
import traceback
import urllib2

from third_party import colorama

import detect_host_arch
import gclient_utils
import scm


DEPOT_TOOLS = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(DEPOT_TOOLS, 'monitoring.cfg')
UPLOAD_SCRIPT = os.path.join(DEPOT_TOOLS, 'upload_monitoring_data.py')

APP_URL = 'https://cit-cli-metrics.appspot.com'

DISABLE_MONITORING = os.environ.get('DEPOT_TOOLS_MONITORING') == '0'
DEFAULT_COUNTDOWN = 10


class Metrics(object):
  def __init__(self):
    self._metrics_lock = threading.Lock()
    self._reported_metrics = {}

  def add(self, name, value):
    with self._metrics_lock:
      self._reported_metrics[name] = value

  def get_all_metrics(self):
    return self._reported_metrics

metrics = Metrics()


class Config(object):
  def __init__(self):
    self._initialized = False
    self._config = {}

  def ensure_initialized(self):
    if self._initialized:
      return

    try:
      with open(CONFIG_FILE) as f:
        self._config = json.load(f)
    except (IOError, ValueError):
      print "WARNING: Your monitoring.cfg file didn't exist or was invalid.",
      print "A new one has been created."
      self._config = {}

    if 'is-googler' not in self._config:
      # /should-upload is only accessible from Google IPs, so we only need to
      # check if we can reach the page. An external developer would get access
      # denied.
      try:
        req = urllib2.urlopen(APP_URL + '/should-upload')
        self._config['is-googler'] = req.getcode() == 200
      except (urllib2.URLError, urllib2.HTTPError):
        self._config['is-googler'] = False

    # Make sure the config variables we need are present, and initialize them to
    # safe values otherwise.
    self._config.setdefault('countdown', DEFAULT_COUNTDOWN)
    self._config.setdefault('opt-in', None)

    self._initialized = True

  @property
  def is_googler(self):
    self.ensure_initialized()
    return self._config['is-googler']

  @property
  def opted_in(self):
    self.ensure_initialized()
    return self._config['opt-in']

  @opted_in.setter
  def opted_in(self, value):
    self.ensure_initialized()
    self._config['opt-in'] = value
    with open(CONFIG_FILE, 'w') as f:
      json.dump(self._config, f)

  @property
  def countdown(self):
    self.ensure_initialized()
    return self._config['countdown']

  def decrease_countdown(self):
    self.ensure_initialized()
    if self._config == 0:
      return
    self._config['countdown'] -= 1
    with open(CONFIG_FILE, 'w') as f:
      json.dump(self._config, f)

config = Config()


def _get_python_version():
  """Return the python version in the major.minor.micro format."""
  return '{v.major}.{v.minor}.{v.micro}'.format(v=sys.version_info)

def _return_code_from_exception(exception):
  """Returns the exit code that would result of raising the exception."""
  if exception is None:
    return 0
  if isinstance(exception[1], SystemExit):
    return exception[1].code
  return 1

def _seconds_to_weeks(duration):
  """Transform a |duration| from seconds to weeks approximately.

  Drops the lowest 19 bits of the integer representation, which ammounts to
  about 6 days.
  """
  return int(duration) >> 19

def _get_repo_timestamp(path_to_repo):
  """Get an approximate timestamp for the upstream of |path_to_repo|.

  Returns the top two bits of the timestamp of the HEAD for the upstream of the
  branch path_to_repo is checked out at.
  """
  # Get the upstream for the current branch. If we're not in a branch, fallback
  # to HEAD.
  try:
    upstream = scm.GIT.GetUpstreamBranch(path_to_repo)
  except subprocess2.CalledProcessError:
    upstream = 'HEAD'

  # Get the timestamp of the HEAD for the upstream of the current branch.
  p = subprocess.Popen(
      ['git', '-C', path_to_repo, 'log', '-n1', upstream, '--format=%at'],
      stdout=subprocess.PIPE, stderr=subprocess.PIPE)
  stdout, _ = p.communicate()

  # If there was an error, give up.
  if p.returncode != 0:
    return None

  # Get the age of the checkout in weeks.
  return _seconds_to_weeks(stdout.strip())

def _upload_monitoring_data():
  """Upload the monitoring data to the AppEngine app."""
  subprocess.Popen(
      [sys.executable, UPLOAD_SCRIPT, json.dumps(metrics.get_all_metrics())],
      stdout=subprocess.PIPE, stderr=subprocess.PIPE)

def _print_notice():
  """Print a notice to let the user know the status of monitoring."""
  colorama.init()
  print colorama.Fore.RED + '\033[1m'
  print "*****************************************************"
  if config.countdown:
    print "*  METRICS COLLECTION WILL START IN %2d EXECUTIONS   *" % (
        config.countdown)
  else:
    print "*      METRICS COLLECTION IS TAKING PLACE           *"
  print "*                                                   *"
  print "* For more information, and for how to disable this *"
  print "* message, please see monitoring.README.md in your  *"
  print "* depot_tools checkout.                             *"
  print "*****************************************************"

def report_metrics(command_name):
  """Wraps a function execution and uploads monitoring data after completion.
  """
  def _decorator(func):
    # Needed to preserve the __name__ and __doc__ attributes of func.
    @functools.wraps(func)
    def _inner(*args, **kwargs):
      metrics.add('command', command_name)
      try:
        start = time.time()
        func(*args, **kwargs)
        exception = None
      # pylint: disable=bare-except
      except:
        exception = sys.exc_info()
      finally:
        metrics.add('execution_time', time.time() - start)

      # Print the exception before the monitoring notice, so that the notice is
      # clearly visible even if gclient fails.
      if exception and not isinstance(exception[1], SystemExit):
        traceback.print_exception(*exception)

      exit_code = _return_code_from_exception(exception)
      metrics.add('exit_code', exit_code)

      # Print the monitoring notice only if the user has not explicitly opted in
      # or out.
      if config.opted_in is None:
        _print_notice()
        config.decrease_countdown()

      # Add metrics regarding environment information.
      metrics.add('timestamp', _seconds_to_weeks(time.time()))
      metrics.add('python_version', _get_python_version())
      metrics.add('host_os', gclient_utils.GetMacWinOrLinux())
      metrics.add('host_arch', detect_host_arch.HostArch())
      metrics.add('depot_tools_age', _get_repo_timestamp(DEPOT_TOOLS))

      _upload_monitoring_data()
      sys.exit(exit_code)

    if DISABLE_MONITORING:
      return func
    # If the user has opted out or the user is not a googler, then there is no
    # need to do anything.
    if config.opted_in == False or not config.is_googler:
      return func
    return _inner
  return _decorator
