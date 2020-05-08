#!/usr/bin/env vpython3
# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Unit tests for git_cache.py"""

import logging
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest

if sys.version_info.major == 2:
  import mock
  import Queue
else:
  from unittest import mock
  import queue as Queue

DEPOT_TOOLS_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, DEPOT_TOOLS_ROOT)

from testing_support import coverage_utils
import git_cache


class LockfileTest(unittest.TestCase):
  def setUp(self):
    self.cache_dir = tempfile.mkdtemp(prefix='git_cache_test_lock')
    self.addCleanup(shutil.rmtree, self.cache_dir, ignore_errors=True)

  def testLock(self):
    l1 = git_cache.Lockfile(self.cache_dir)
    l2 = git_cache.Lockfile(self.cache_dir)

    with l1.lock():
      with self.assertRaises(AssertionError):
        with l1.lock():
          # The same instance is able to lock.
          pass

      with self.assertRaises(git_cache.LockError):
        # A different instance is not able to lock
        with l2.lock():
          pass

    with l2.lock():
      pass

  @mock.patch('time.sleep')
  def testLockConcurrent(self, sleep_mock):
    '''testLockConcurrent simulates what happens when two separate processes try
    to acquire the same file lock with timeout.'''
    # Queues q_f1 and q_sleep are used to controll execution of individual
    # threads.
    q_f1 = Queue.Queue()
    q_sleep = Queue.Queue()
    results = Queue.Queue()

    def side_effect(arg):
      '''side_effect is called when with l.lock is blocked. In this unit test
      case, it comes from f2.'''
      logging.debug('sleep: started')
      q_sleep.put(True)
      logging.debug('sleep: waiting for q_sleep to be consumed')
      q_sleep.join()
      logging.debug('sleep: exiting')

    sleep_mock.side_effect = side_effect

    def f1():
      '''f1 enters first in l.lock (controlled via q_f1). It then waits for
      side_effect to put a message in queue q_sleep.'''
      logging.debug('f1 started')
      l = git_cache.Lockfile(self.cache_dir, timeout=1)
      logging.debug('locking in f1')
      with l.lock():
        logging.debug('f1: locked')
        q_f1.put(True)
        logging.debug('f1: waiting on q_f1 to be consumed')
        q_f1.join()
        logging.debug('f1: done waiting on q_f1, getting q_sleep')
        q_sleep.get(timeout=1)
        q_sleep.task_done()
        results.put(True)
        logging.debug('f1: exiting')

    def f2():
      '''f2 enters second in l.lock (controlled by q_f1).'''
      logging.debug('f2: started')
      l = git_cache.Lockfile(self.cache_dir, timeout=1)
      logging.debug('f2: consuming q_f1')
      q_f1.get(timeout=1)  # wait for f1 to execute lock
      q_f1.task_done()
      logging.debug('f2: done waiting for q_f1, locking')
      with l.lock():
        logging.debug('f2: locked')
        results.put(True)

    t1 = threading.Thread(target=f1)
    t1.start()
    t2 = threading.Thread(target=f2)
    t2.start()
    t1.join()
    t2.join()

    self.assertEqual(2, results.qsize())
    sleep_mock.assert_called_once_with(1)


class GitCacheTest(unittest.TestCase):
  def setUp(self):
    self.cache_dir = tempfile.mkdtemp(prefix='git_cache_test_')
    self.addCleanup(shutil.rmtree, self.cache_dir, ignore_errors=True)
    self.origin_dir = tempfile.mkdtemp(suffix='origin.git')
    self.addCleanup(shutil.rmtree, self.origin_dir, ignore_errors=True)
    git_cache.Mirror.SetCachePath(self.cache_dir)

  def git(self, cmd, cwd=None):
    cwd = cwd or self.origin_dir
    git = 'git.bat' if sys.platform == 'win32' else 'git'
    subprocess.check_call([git] + cmd, cwd=cwd)

  def testParseFetchSpec(self):
    testData = [
        ([], []),
        (['master'], [('+refs/heads/master:refs/heads/master',
                       r'\+refs/heads/master:.*')]),
        (['master/'], [('+refs/heads/master:refs/heads/master',
                       r'\+refs/heads/master:.*')]),
        (['+master'], [('+refs/heads/master:refs/heads/master',
                       r'\+refs/heads/master:.*')]),
        (['refs/heads/*'], [('+refs/heads/*:refs/heads/*',
                            r'\+refs/heads/\*:.*')]),
        (['foo/bar/*', 'baz'], [('+refs/heads/foo/bar/*:refs/heads/foo/bar/*',
                                r'\+refs/heads/foo/bar/\*:.*'),
                               ('+refs/heads/baz:refs/heads/baz',
                                r'\+refs/heads/baz:.*')]),
        (['refs/foo/*:refs/bar/*'], [('+refs/foo/*:refs/bar/*',
                                      r'\+refs/foo/\*:.*')])
        ]

    mirror = git_cache.Mirror('test://phony.example.biz')
    for fetch_specs, expected in testData:
      mirror = git_cache.Mirror('test://phony.example.biz', refs=fetch_specs)
      self.assertEqual(mirror.fetch_specs, set(expected))

  def testPopulate(self):
    self.git(['init', '-q'])
    with open(os.path.join(self.origin_dir, 'foo'), 'w') as f:
      f.write('touched\n')
    self.git(['add', 'foo'])
    self.git(['commit', '-m', 'foo'])

    mirror = git_cache.Mirror(self.origin_dir)
    mirror.populate()

  def testPopulateResetFetchConfig(self):
    self.git(['init', '-q'])
    with open(os.path.join(self.origin_dir, 'foo'), 'w') as f:
      f.write('touched\n')
    self.git(['add', 'foo'])
    self.git(['commit', '-m', 'foo'])

    mirror = git_cache.Mirror(self.origin_dir)
    mirror.populate()

    # Add a bad refspec to the cache's fetch config.
    cache_dir = os.path.join(
        self.cache_dir, mirror.UrlToCacheDir(self.origin_dir))
    self.git(['config', '--add', 'remote.origin.fetch',
              '+refs/heads/foo:refs/heads/foo'],
             cwd=cache_dir)

    mirror.populate(reset_fetch_config=True)

  def testPopulateTwice(self):
    self.git(['init', '-q'])
    with open(os.path.join(self.origin_dir, 'foo'), 'w') as f:
      f.write('touched\n')
    self.git(['add', 'foo'])
    self.git(['commit', '-m', 'foo'])

    mirror = git_cache.Mirror(self.origin_dir)
    mirror.populate()

    mirror.populate()

  def _makeGitRepoWithTag(self):
    self.git(['init', '-q'])
    with open(os.path.join(self.origin_dir, 'foo'), 'w') as f:
      f.write('touched\n')
    self.git(['add', 'foo'])
    self.git(['commit', '-m', 'foo'])
    self.git(['tag', 'TAG'])
    self.git(['pack-refs'])

  def testPopulateFetchTagsByDefault(self):
    self._makeGitRepoWithTag()

    # Default behaviour includes tags.
    mirror = git_cache.Mirror(self.origin_dir)
    mirror.populate()

    cache_dir = os.path.join(self.cache_dir,
                             mirror.UrlToCacheDir(self.origin_dir))
    self.assertTrue(os.path.exists(cache_dir + '/refs/tags/TAG'))

  def testPopulateFetchWithoutTags(self):
    self._makeGitRepoWithTag()

    # Ask to not include tags.
    mirror = git_cache.Mirror(self.origin_dir)
    mirror.populate(no_fetch_tags=True)

    cache_dir = os.path.join(self.cache_dir,
                             mirror.UrlToCacheDir(self.origin_dir))
    self.assertFalse(os.path.exists(cache_dir + '/refs/tags/TAG'))

  def testPopulateResetFetchConfigEmptyFetchConfig(self):
    self.git(['init', '-q'])
    with open(os.path.join(self.origin_dir, 'foo'), 'w') as f:
      f.write('touched\n')
    self.git(['add', 'foo'])
    self.git(['commit', '-m', 'foo'])

    mirror = git_cache.Mirror(self.origin_dir)
    mirror.populate(reset_fetch_config=True)


class GitCacheDirTest(unittest.TestCase):
  def setUp(self):
    try:
      delattr(git_cache.Mirror, 'cachepath')
    except AttributeError:
      pass
    super(GitCacheDirTest, self).setUp()

  def tearDown(self):
    try:
      delattr(git_cache.Mirror, 'cachepath')
    except AttributeError:
      pass
    super(GitCacheDirTest, self).tearDown()

  def test_git_config_read(self):
    (fd, tmpFile) = tempfile.mkstemp()
    old = git_cache.Mirror._GIT_CONFIG_LOCATION
    try:
      try:
        os.write(fd, b'[cache]\n  cachepath="hello world"\n')
      finally:
        os.close(fd)

      git_cache.Mirror._GIT_CONFIG_LOCATION = ['-f', tmpFile]

      self.assertEqual(git_cache.Mirror.GetCachePath(), 'hello world')
    finally:
      git_cache.Mirror._GIT_CONFIG_LOCATION = old
      os.remove(tmpFile)

  def test_environ_read(self):
    path = os.environ.get('GIT_CACHE_PATH')
    config = os.environ.get('GIT_CONFIG')
    try:
      os.environ['GIT_CACHE_PATH'] = 'hello world'
      os.environ['GIT_CONFIG'] = 'disabled'

      self.assertEqual(git_cache.Mirror.GetCachePath(), 'hello world')
    finally:
      for name, val in zip(('GIT_CACHE_PATH', 'GIT_CONFIG'), (path, config)):
        if val is None:
          os.environ.pop(name, None)
        else:
          os.environ[name] = val

  def test_manual_set(self):
    git_cache.Mirror.SetCachePath('hello world')
    self.assertEqual(git_cache.Mirror.GetCachePath(), 'hello world')

  def test_unconfigured(self):
    path = os.environ.get('GIT_CACHE_PATH')
    config = os.environ.get('GIT_CONFIG')
    try:
      os.environ.pop('GIT_CACHE_PATH', None)
      os.environ['GIT_CONFIG'] = 'disabled'

      with self.assertRaisesRegexp(RuntimeError, 'cache\.cachepath'):
        git_cache.Mirror.GetCachePath()

      # negatively cached value still raises
      with self.assertRaisesRegexp(RuntimeError, 'cache\.cachepath'):
        git_cache.Mirror.GetCachePath()
    finally:
      for name, val in zip(('GIT_CACHE_PATH', 'GIT_CONFIG'), (path, config)):
        if val is None:
          os.environ.pop(name, None)
        else:
          os.environ[name] = val


class MirrorTest(unittest.TestCase):
  def test_same_cache_for_authenticated_and_unauthenticated_urls(self):
    # GoB can fetch a repo via two different URLs; if the url contains '/a/'
    # it forces authenticated access instead of allowing anonymous access,
    # even in the case where a repo is public. We want this in order to make
    # sure bots are authenticated and get the right quotas. However, we
    # only want to maintain a single cache for the repo.
    self.assertEqual(git_cache.Mirror.UrlToCacheDir(
        'https://chromium.googlesource.com/a/chromium/src.git'),
        'chromium.googlesource.com-chromium-src')


if __name__ == '__main__':
  logging.basicConfig(
      level=logging.DEBUG if '-v' in sys.argv else logging.ERROR)
  sys.exit(coverage_utils.covered_main((
    os.path.join(DEPOT_TOOLS_ROOT, 'git_cache.py')
  ), required_percentage=0))
