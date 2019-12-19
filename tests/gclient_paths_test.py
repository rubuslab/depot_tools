#!/usr/bin/env vpython3
# coding=utf-8
# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import gclient_paths
import gclient_utils
import subprocess2

from third_party import mock

if sys.version_info.major == 2:
  from StringIO import StringIO
else:
  from io import StringIO


EXCEPTION = subprocess2.CalledProcessError(
    128, ['cmd'], 'cwd', 'stdout', 'stderr')


class TestBase(unittest.TestCase):
  def setUp(self):
    super(TestBase, self).setUp()
    self.cwd = None
    self.file_tree = {}
    mock.patch('gclient_utils.FileRead', self.read).start()
    mock.patch('os.environ', {}).start()
    mock.patch('os.getcwd', self.getcwd).start()
    mock.patch('os.path.exists', self.exists).start()
    mock.patch('os.path.realpath', side_effect=lambda path: path).start()
    mock.patch('subprocess2.check_output').start()
    mock.patch('sys.platform', '').start()
    mock.patch('sys.stderr', StringIO()).start()
    self.addCleanup(mock.patch.stopall)

  def getcwd(self):
    return self.cwd.replace('/', os.sep)

  def exists(self, path):
    return path.replace(os.sep, '/') in self.file_tree

  def read(self, path):
    return self.file_tree[path.replace(os.sep, '/')]

  def assertPathEqual(self, expected, actual):
    self.assertEqual(expected.replace('/', os.sep), actual)


class FindGclientRootTest(TestBase):
  def testFindGclientRoot(self):
    self.file_tree = {'root/.gclient': ''}
    self.assertPathEqual('root', gclient_paths.FindGclientRoot('root'))

  def testGclientRootInParentDir(self):
    self.file_tree = {
      'root/.gclient': '',
      'root/.gclient_entries': 'entries = {"foo": "..."}',
    }
    self.assertPathEqual('root', gclient_paths.FindGclientRoot('root/foo/bar'))

  def testGclientRootInParentDir_NotInGclientEntries(self):
    self.file_tree = {
      'root/.gclient': '',
      'root/.gclient_entries': 'entries = {"foo": "..."}',
    }
    self.assertIsNone(gclient_paths.FindGclientRoot('root/bar/baz'))

  def testGclientRootInParentDir_NoGclientEntriesFile(self):
    self.file_tree = {'root/.gclient': ''}
    self.assertPathEqual('root', gclient_paths.FindGclientRoot('root/x/y/z'))
    self.assertEqual(
        '%s missing, .gclient file in parent directory root might not be the '
        'file you want to use.\n' % os.path.join('root', '.gclient_entries'),
        sys.stderr.getvalue())

  def testGclientRootInParentDir_ErrorWhenParsingEntries(self):
    self.file_tree = {
      'root/.gclient': '',
      'root/.gclient_entries': ':P',
    }
    with self.assertRaises(Exception):
      gclient_paths.FindGclientRoot('root/foo/bar')

  def testRootNotFound(self):
    self.assertIsNone(gclient_paths.FindGclientRoot('root/x/y/z'))


class GetGClientPrimarySolutionNameTest(TestBase):
  def testGetGClientPrimarySolutionName(self):
    self.file_tree = {'root/.gclient': 'solutions = [{"name": "foo"}]'}
    self.assertPathEqual(
      'foo', gclient_paths.GetGClientPrimarySolutionName('root'))

  def testNoSolutionsInGclientFile(self):
    self.file_tree = {'root/.gclient': ''}
    self.assertIsNone(gclient_paths.GetGClientPrimarySolutionName('root'))


class GetPrimarySolutionPathTest(TestBase):
  def testGetPrimarySolutionPath(self):
    self.file_tree = {'root/.gclient': 'solutions = [{"name": "foo"}]'}
    self.cwd = 'root'

    self.assertPathEqual('root/foo', gclient_paths.GetPrimarySolutionPath())

  def testSolutionNameDefaultsToSrc(self):
    self.file_tree = {'root/.gclient': ''}
    self.cwd = 'root'

    self.assertPathEqual('root/src', gclient_paths.GetPrimarySolutionPath())

  def testGclientRootNotFound_GitRootHasBuildtools(self):
    self.file_tree = {'foo/buildtools': ''}
    self.cwd = 'foo/bar'
    subprocess2.check_output.return_value = b'foo\n'

    self.assertPathEqual('foo', gclient_paths.GetPrimarySolutionPath())

  def testGclientRootNotFound_NoBuildtools(self):
    self.cwd = 'foo/bar'
    subprocess2.check_output.return_value = b'foo\n'

    self.assertIsNone(gclient_paths.GetPrimarySolutionPath())

  def testGclientRootNotFound_NotInAGitRepo_CurrentDirHasBuildtools(self):
    self.file_tree = {'foo/bar/buildtools': ''}
    self.cwd = 'foo/bar'
    subprocess2.check_output.side_effect = EXCEPTION

    self.assertPathEqual('foo/bar', gclient_paths.GetPrimarySolutionPath())

  def testGclientRootNotFound_NotInAGitRepo_NoBuildtools(self):
    self.cwd = 'foo'
    subprocess2.check_output.side_effect = EXCEPTION

    self.assertIsNone(gclient_paths.GetPrimarySolutionPath())


class GetBuildtoolsPathTest(TestBase):
  def testEnvVarOverride(self):
    os.environ = {'CHROMIUM_BUILDTOOLS_PATH': 'foo'}

    self.assertPathEqual('foo', gclient_paths.GetBuildtoolsPath())

  def testNoSolutionsFound(self):
    self.cwd = 'foo/bar'
    subprocess2.check_output.side_effect = EXCEPTION

    self.assertIsNone(gclient_paths.GetBuildtoolsPath())

  def testBuildtoolsInSolution(self):
    self.file_tree = {'root/.gclient': '', 'root/src/buildtools': ''}
    self.cwd = 'root/src/foo'

    self.assertPathEqual(
        'root/src/buildtools', gclient_paths.GetBuildtoolsPath())

  def testBuildtoolsInGclientRoot(self):
    self.file_tree = {'root/.gclient': '', 'root/buildtools': ''}
    self.cwd = 'root/src/bar'

    self.assertPathEqual('root/buildtools', gclient_paths.GetBuildtoolsPath())

  def testNoBuildtools(self):
    self.file_tree = {'root/.gclient': ''}
    self.cwd = 'root/foo/bar'

    self.assertIsNone(gclient_paths.GetBuildtoolsPath())


class GetBuildtoolsPlatformBinaryPath(TestBase):
  def testNoBuildtoolsPath(self):
    self.file_tree = {'root/.gclient': ''}
    self.cwd = 'root/foo/bar'
    self.assertIsNone(gclient_paths.GetBuildtoolsPlatformBinaryPath())

  def testWin(self):
    self.file_tree = {'root/.gclient': '', 'root/buildtools': ''}
    self.cwd = 'root'
    sys.platform = 'win'

    self.assertPathEqual(
        'root/buildtools/win', gclient_paths.GetBuildtoolsPlatformBinaryPath())

  def testCygwin(self):
    self.file_tree = {'root/.gclient': '', 'root/buildtools': ''}
    self.cwd = 'root'
    sys.platform = 'cygwin'

    self.assertPathEqual(
        'root/buildtools/win', gclient_paths.GetBuildtoolsPlatformBinaryPath())

  def testMac(self):
    self.file_tree = {'root/.gclient': '', 'root/buildtools': ''}
    self.cwd = 'root'
    sys.platform = 'darwin'

    self.assertPathEqual(
        'root/buildtools/mac', gclient_paths.GetBuildtoolsPlatformBinaryPath())

  def testLinux(self):
    self.file_tree = {'root/.gclient': '', 'root/buildtools': ''}
    self.cwd = 'root'
    sys.platform = 'linux'

    self.assertPathEqual(
        'root/buildtools/linux64',
        gclient_paths.GetBuildtoolsPlatformBinaryPath())

  def testError(self):
    self.file_tree = {'root/.gclient': '', 'root/buildtools': ''}
    self.cwd = 'root'
    sys.platform = 'foo'

    with self.assertRaises(gclient_utils.Error, msg='Unknown platform: foo'):
      gclient_paths.GetBuildtoolsPlatformBinaryPath()


class GetExeSuffixTest(TestBase):
  def testGetExeSuffix(self):
    sys.platform = 'win'
    self.assertEqual('.exe', gclient_paths.GetExeSuffix())

    sys.platform = 'cygwin'
    self.assertEqual('.exe', gclient_paths.GetExeSuffix())

    sys.platform = 'foo'
    self.assertEqual('', gclient_paths.GetExeSuffix())


if __name__ == '__main__':
  unittest.main()
