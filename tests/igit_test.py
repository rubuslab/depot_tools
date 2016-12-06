#!/usr/bin/python

import unittest
import sys
import os
import tempfile
import shutil

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    'testing_support'))

import igit
import mock

TRACE_LOG="""
14:09:04.511592 git.c:350               trace: built-in: git 'fetch'
14:09:04.515500 run-command.c:336       trace: run_command: 'git-remote-https' 'origin' 'https://chromium.googlesource.com/chromium/tools/depot_tools.git'
14:09:05.061395 run-command.c:336       trace: run_command: 'rev-list' '--objects' '--stdin' '--not' '--all' '--quiet'
14:09:05.061899 exec_cmd.c:120          trace: exec: 'git' 'rev-list' '--objects' '--stdin' '--not' '--all' '--quiet'
14:09:05.064036 git.c:350               trace: built-in: git 'rev-list' '--objects' '--stdin' '--not' '--all' '--quiet'
14:09:05.066152 run-command.c:336       trace: run_command: 'fetch-pack' '--stateless-rpc' '--stdin' '--lock-pack' '--include-tag' '--thin' 'https://chromium.googlesource.com/chromium/tools/depot_tools.git/'
14:09:05.066805 exec_cmd.c:120          trace: exec: 'git' 'fetch-pack' '--stateless-rpc' '--stdin' '--lock-pack' '--include-tag' '--thin' 'https://chromium.googlesource.com/chromium/tools/depot_tools.git/'
14:09:05.068971 git.c:350               trace: built-in: git 'fetch-pack' '--stateless-rpc' '--stdin' '--lock-pack' '--include-tag' '--thin' 'https://chromium.googlesource.com/chromium/tools/depot_tools.git/'
14:09:05.218574 run-command.c:336       trace: run_command: 'index-pack' '--stdin' '-v' '--fix-thin' '--keep=fetch-pack 6380 on oddish.mtv.corp.google.com' '--pack_header=2,329'
14:09:05.219041 exec_cmd.c:120          trace: exec: 'git' 'index-pack' '--stdin' '-v' '--fix-thin' '--keep=fetch-pack 6380 on oddish.mtv.corp.google.com' '--pack_header=2,329'
14:09:05.221196 git.c:350               trace: built-in: git 'index-pack' '--stdin' '-v' '--fix-thin' '--keep=fetch-pack 6380 on oddish.mtv.corp.google.com' '--pack_header=2,329'
14:09:05.601519 run-command.c:336       trace: run_command: 'rev-list' '--objects' '--stdin' '--not' '--all'
14:09:05.601914 exec_cmd.c:120          trace: exec: 'git' 'rev-list' '--objects' '--stdin' '--not' '--all'
14:09:05.603984 git.c:350               trace: built-in: git 'rev-list' '--objects' '--stdin' '--not' '--all'
14:09:05.616635 run-command.c:952       run_processes_parallel: preparing to run up to 1 tasks
14:09:05.616704 run-command.c:984       run_processes_parallel: done
14:09:05.616786 run-command.c:336       trace: run_command: 'gc' '--auto'
14:09:05.617105 exec_cmd.c:120          trace: exec: 'git' 'gc' '--auto'
14:09:05.618508 git.c:350               trace: built-in: git 'gc' '--auto'
"""


class IGitUnitTests(unittest.TestCase):
  def setUp(self):
    self.tempdir = tempfile.mkdtemp()

  def cleanUp(self):
    shutil.rmtree(self.tempdir)

  @mock.patch('time.time')
  def test_tracker_startup(self, time_mock):
    trace_file = os.path.join(self.tempdir, 'trace.log')
    packet_file = os.path.join(self.tempdir, 'packet.log')
    time_mock.return_value = 1000
    tracker = igit.Tracker(trace_file, packet_file)
    self.assertFalse(tracker.should_kill())
    time_mock.return_value = 1500
    self.assertTrue(tracker.should_kill())
    self.assertEquals(tracker.kill_reason, 'Startup timeout')

  @mock.patch('os.path.getmtime')
  @mock.patch('time.time')
  def test_tracker_basic(self, time_mock, getmtime_mock):
    trace_file = os.path.join(self.tempdir, 'trace.log')
    packet_file = os.path.join(self.tempdir, 'packet.log')
    time_mock.return_value = 1000
    tracker = igit.Tracker(trace_file, packet_file)
    self.assertFalse(tracker.should_kill())
    self.assertEquals(tracker.state, igit.Tracker.NOT_STARTED)
    with open(trace_file, 'w') as f:
      f.write(''.join(TRACE_LOG.splitlines()[:6]))
    with open(packet_file, 'w') as f:
      f.write('foobar\n')
    self.assertFalse(tracker.should_kill())
    self.assertEquals(tracker.state, igit.Tracker.NOT_ACTIVE)
    self.assertFalse(tracker.should_kill())
    self.assertEquals(tracker.state, igit.Tracker.ACTIVE)
    getmtime_mock.assert_not_called()
    getmtime_mock.return_value = 1050
    time_mock.return_value = 1060
    self.assertFalse(tracker.should_kill())
    self.assertEquals(tracker.state, igit.Tracker.ACTIVE)
    getmtime_mock.assert_called()
    time_mock.return_value = 1100
    self.assertTrue(tracker.should_kill())
    self.assertEquals(
        tracker.kill_reason, 'Git remote https timeout (50 seconds)')

  @mock.patch('os.path.getmtime')
  @mock.patch('time.time')
  def test_tracker_revert(self, time_mock, getmtime_mock):
    trace_file = os.path.join(self.tempdir, 'trace.log')
    packet_file = os.path.join(self.tempdir, 'packet.log')
    time_mock.return_value = 1000
    tracker = igit.Tracker(trace_file, packet_file)
    with open(trace_file, 'w') as f:
      f.write(''.join(TRACE_LOG.splitlines()[:6]))
    with open(packet_file, 'w') as f:
      f.write('foobar\n')
    self.assertFalse(tracker.should_kill())
    self.assertEquals(tracker.state, igit.Tracker.NOT_ACTIVE)
    self.assertFalse(tracker.should_kill())
    self.assertEquals(tracker.state, igit.Tracker.ACTIVE)
    getmtime_mock.return_value = 1050
    time_mock.return_value = 1060
    with open(trace_file, 'w') as f:
      f.write(''.join(TRACE_LOG.splitlines()))
    self.assertFalse(tracker.should_kill())
    self.assertEquals(tracker.state, igit.Tracker.NOT_ACTIVE)

  def test_use_igit(self):
    self.assertTrue(igit.use_igit(['igit.py', 'fetch']))
    self.assertFalse(igit.use_igit(['igit.py']))
    self.assertFalse(igit.use_igit(['igit.py', 'checkout']))

if __name__ == '__main__':
  unittest.main()
