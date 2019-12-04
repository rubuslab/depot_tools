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
    self.file_tree = {}
    mock.patch('gclient_utils.FileRead',
               side_effect=lambda path: self.file_tree[path]).start()
    mock.patch('os.environ', {}).start()
    mock.patch('os.getcwd').start()
    mock.patch('os.path.exists',
               side_effect=lambda path: path in self.file_tree).start()
    mock.patch('os.path.realpath', side_effect=lambda path: path).start()
    mock.patch('subprocess2.check_output').start()
    mock.patch('sys.platform', '').start()
    mock.patch('sys.stderr', StringIO()).start()
    self.addCleanup(mock.patch.stopall)


class FindGclientRootTest(TestBase):
  def testFindGclientRoot(self):
    self.file_tree = {'/root/.gclient': ''}
    self.assertEqual('/root', gclient_paths.FindGclientRoot('/root'))

  def testGclientRootInParentDir(self):
    self.file_tree = {
      '/root/.gclient': '',
      '/root/.gclient_entries': 'entries = {"foo": "..."}',
    }
    self.assertEqual('/root', gclient_paths.FindGclientRoot('/root/foo/bar'))

  def testGclientRootInParentDir_NotInGclientEntries(self):
    self.file_tree = {
      '/root/.gclient': '',
      '/root/.gclient_entries': 'entries = {"foo": "..."}',
    }
    self.assertIsNone(gclient_paths.FindGclientRoot('/root/bar/baz'))

  def testGclientRootInParentDir_NoGclientEntriesFile(self):
    self.file_tree = {'/root/.gclient': ''}
    self.assertEqual('/root', gclient_paths.FindGclientRoot('/root/x/y/z'))
    self.assertEqual(
        '/root/.gclient_entries missing, .gclient file in parent directory '
        '/root might not be the file you want to use.\n',
        sys.stderr.getvalue())

  def testGclientRootInParentDir_ErrorWhenParsingEntries(self):
    self.file_tree = {
      '/root/.gclient': '',
      '/root/.gclient_entries': ':P',
    }
    with self.assertRaises(Exception):
      gclient_paths.FindGclientRoot('/root/foo/bar')

  def testRootNotFound(self):
    self.assertIsNone(gclient_paths.FindGclientRoot('/root/x/y/z'))


class GetGClientPrimarySolutionNameTest(TestBase):
  def testGetGClientPrimarySolutionName(self):
    self.file_tree = {'/root/.gclient': 'solutions = [{"name": "foo"}]'}
    self.assertEqual(
      'foo', gclient_paths.GetGClientPrimarySolutionName('/root'))

  def testNoSolutionsInGclientFile(self):
    self.file_tree = {'/root/.gclient': ''}
    self.assertIsNone(gclient_paths.GetGClientPrimarySolutionName('/root'))


class GetPrimarySolutionPathTest(TestBase):
  def testGetPrimarySolutionPath(self):
    self.file_tree = {'/root/.gclient': 'solutions = [{"name": "foo"}]'}
    os.getcwd.return_value = '/root'

    self.assertEqual('/root/foo', gclient_paths.GetPrimarySolutionPath())

  def testSolutionNameDefaultsToSrc(self):
    self.file_tree = {'/root/.gclient': ''}
    os.getcwd.return_value = '/root'

    self.assertEqual('/root/src', gclient_paths.GetPrimarySolutionPath())

  def testGclientRootNotFound_GitRootHasBuildtools(self):
    self.file_tree = {'/foo/buildtools': ''}
    os.getcwd.return_value = '/foo/bar'
    subprocess2.check_output.return_value = b'/foo\n'

    self.assertEqual('/foo', gclient_paths.GetPrimarySolutionPath())

  def testGclientRootNotFound_NoBuildtools(self):
    os.getcwd.return_value = '/foo/bar'
    subprocess2.check_output.return_value = b'/foo\n'

    self.assertIsNone(gclient_paths.GetPrimarySolutionPath())

  def testGclientRootNotFound_NotInAGitRepo_CurrentDirHasBuildtools(self):
    self.file_tree = {'/foo/bar/buildtools': ''}
    os.getcwd.return_value = '/foo/bar'
    subprocess2.check_output.side_effect = EXCEPTION

    self.assertEqual('/foo/bar', gclient_paths.GetPrimarySolutionPath())

  def testGclientRootNotFound_NotInAGitRepo_NoBuildtools(self):
    os.getcwd.return_value = '/foo'
    subprocess2.check_output.side_effect = EXCEPTION

    self.assertIsNone(gclient_paths.GetPrimarySolutionPath())


class GetBuildtoolsPathTest(TestBase):
  def testEnvVarOverride(self):
    os.environ = {'CHROMIUM_BUILDTOOLS_PATH': '/foo'}

    self.assertEqual('/foo', gclient_paths.GetBuildtoolsPath())

  def testNoSolutionsFound(self):
    os.getcwd.return_value = '/foo/bar'
    subprocess2.check_output.side_effect = EXCEPTION

    self.assertIsNone(gclient_paths.GetBuildtoolsPath())

  def testBuildtoolsInSolution(self):
    self.file_tree = {'/root/.gclient': '', '/root/src/buildtools': ''}
    os.getcwd.return_value = '/root/src/foo'

    self.assertEqual('/root/src/buildtools', gclient_paths.GetBuildtoolsPath())

  def testBuildtoolsInGclientRoot(self):
    self.file_tree = {'/root/.gclient': '', '/root/buildtools': ''}
    os.getcwd.return_value = '/root/src/bar'

    self.assertEqual('/root/buildtools', gclient_paths.GetBuildtoolsPath())

  def testNoBuildtools(self):
    self.file_tree = {'/root/.gclient': ''}
    os.getcwd.return_value = '/root/foo/bar'

    self.assertIsNone(gclient_paths.GetBuildtoolsPath())


class GetBuildtoolsPlatformBinaryPath(TestBase):
  def testNoBuildtoolsPath(self):
    self.file_tree = {'/root/.gclient': ''}
    os.getcwd.return_value = '/root/foo/bar'
    self.assertIsNone(gclient_paths.GetBuildtoolsPlatformBinaryPath())

  def testWin(self):
    self.file_tree = {'/root/.gclient': '', '/root/buildtools': ''}
    os.getcwd.return_value = '/root'
    sys.platform = 'win'

    self.assertEqual(
        '/root/buildtools/win', gclient_paths.GetBuildtoolsPlatformBinaryPath())

  def testCygwin(self):
    self.file_tree = {'/root/.gclient': '', '/root/buildtools': ''}
    os.getcwd.return_value = '/root'
    sys.platform = 'cygwin'

    self.assertEqual(
        '/root/buildtools/win', gclient_paths.GetBuildtoolsPlatformBinaryPath())

  def testMac(self):
    self.file_tree = {'/root/.gclient': '', '/root/buildtools': ''}
    os.getcwd.return_value = '/root'
    sys.platform = 'darwin'

    self.assertEqual(
        '/root/buildtools/mac', gclient_paths.GetBuildtoolsPlatformBinaryPath())

  def testLinux(self):
    self.file_tree = {'/root/.gclient': '', '/root/buildtools': ''}
    os.getcwd.return_value = '/root'
    sys.platform = 'linux'

    self.assertEqual(
        '/root/buildtools/linux64',
        gclient_paths.GetBuildtoolsPlatformBinaryPath())

  def testError(self):
    self.file_tree = {'/root/.gclient': '', '/root/buildtools': ''}
    os.getcwd.return_value = '/root'
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
