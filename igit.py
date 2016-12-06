#!/usr/bin/python

"""igit - An instrumented git wrapper."""

import os
import sys
import tempfile
import subprocess
import time
import threading
import shutil
import re


class ArgumentError(Exception):
  pass


class TimedPopen(subprocess.Popen):
  """Like subprocess.Popen, but includes a timer."""
  def __init__(self, cmd, *args, **kwargs):
    self._done_event = threading.Event()
    self._wait_thread = threading.Thread(target=self._wait_event)
    self._wait_thread.daemon = True
    try:
      return subprocess.Popen.__init__(self, cmd, *args, **kwargs)
    finally:
      self._wait_thread.start()

  def _wait_event(self):
    self.wait()
    self._done_event.set()

  def check(self, timeout=10):
    self._done_event.wait(timeout)
    return self.poll()


class Tracker(object):
  """Tracks git trace and packet logs to determine if git needs to die."""
  NOT_STARTED = 0
  ACTIVE = 1
  NOT_ACTIVE = 2
  R_ACTIVE = re.compile(r"trace: run_command: 'git-remote-https'")
  R_NOT_ACTIVE= re.compile(r"trace: run_command: 'index-pack'")

  def __init__(self, trace_file, packet_file, timeout=30):
    self.trace_file = trace_file
    self.trace_position = 0
    self.packet_file = packet_file
    self.timeout = timeout

    self.started = time.time()
    self.kill_reason = 'no reason'
    self.state = self.NOT_STARTED

  def read_trace(self):
    if not os.path.exists(self.trace_file):
      return ''
    with open(self.trace_file) as f:
      f.seek(self.trace_position)
      buf = f.read()
      self.trace_position = f.tell()
    return buf

  def new_state(self):
    new_lines = self.read_trace()
    current_state = self.state
    for line in new_lines.splitlines():
      if self.R_ACTIVE.search(line):
        current_state = self.ACTIVE
      if self.R_NOT_ACTIVE.search(line):
        current_state = self.NOT_ACTIVE
    return current_state


  def should_kill(self):
    """The tracker will signal to kill git under the following conditions:

    * The trace/packet files don't appear within the timeout.
    * During active mode, the packet files goes for longer than "timeout"
      between updates.
    """
    if self.state == self.NOT_STARTED:
      if os.path.exists(self.trace_file) and os.path.exists(self.packet_file):
        self.state = self.NOT_ACTIVE
        return False
      if time.time() - self.started > self.timeout:
        self.kill_reason = 'Startup timeout'
        return True

    elif self.state == self.NOT_ACTIVE:
      self.state = self.new_state()

    elif self.state == self.ACTIVE:
      self.state = self.new_state()
      if self.state == self.ACTIVE:
        # Only check if we're still active.
        last_mod = time.time() - os.path.getmtime(self.packet_file)
        if last_mod > self.timeout:
          self.kill_reason = 'Git remote https timeout (%d seconds)' % last_mod
          return True

    return False


def run_git_with_timeout(git_bin, args):
  """This runs git with the given args, with timeouts."""
  tempdir = tempfile.mkdtemp()
  trace_file = os.path.join(tempdir, 'trace.log')
  packet_file = os.path.join(tempdir, 'packet.log')
  tracker = Tracker(trace_file, packet_file)
  env = os.environ.copy()
  env['GIT_TRACE'] = trace_file
  env['GIT_TRACE_PACKET'] = packet_file
  cmd = [git_bin,] + args
  proc = TimedPopen(cmd, env=env, stdout=sys.stdout, stderr=sys.stderr)
  try:
    while True:
      code = proc.check()
      if code is None:
        # Still running
        if tracker.should_kill():
          print 'igit.py: Killing git process due to %s' % tracker.kill_reason
          proc.kill()
          return 1
      else:
        return code
  finally:
    shutil.rmtree(tempdir)


def use_igit(args):
  if len(args) > 1 and args[1] == 'fetch':
    return True
  return False


def which_git():
  """Extract the git binary location out of the envion.

  We do this so that we don't have to pollute the command line arguments.
  """
  git = os.environ.get('TRUE_GIT')
  if not git:
    raise ArgumentError('Missing TRUE_GIT env var.')
  return git


def main():
  git_bin = which_git()
  active = use_igit(sys.argv)
  if active:
    return run_git_with_timeout(git_bin, sys.argv[1:])
  return subprocess.call([git_bin,] + sys.argv[1:])


if __name__ == '__main__':
  sys.exit(main())
