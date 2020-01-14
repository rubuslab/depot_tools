#!/usr/bin/env vpython
# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import os
import sys
import unittest

if sys.version_info.major == 2:
  import mock
else:
  from unittest import mock

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)

import subcommand


class SubcommandTest(unittest.TestCase):
  def setUp(self):
    super(SubcommandTest, self).setUp()
    self.module = mock.Mock(__doc__='Module documentation')
    self.parser = mock.Mock()
    self.sc = subcommand.CommandDispatcher(__name__)
    self.sc.module = self.module

  def testEnumerateCommands(self):
    self.module.CMDfoo_bar = object()
    self.module.CMDbaz = object()
    self.module.CMDaBcDeF_0123 = object()

    expected = {
      'foo-bar': self.module.CMDfoo_bar,
      'baz': self.module.CMDbaz,
      'aBcDeF-0123': self.module.CMDaBcDeF_0123,
      'help': subcommand.CMDhelp,
    }
    self.assertEqual(expected, self.sc.enumerate_commands())

  def testEnumerateCommands_CustomHelp(self):
    self.module.CMDhelp = object()
    self.assertEqual(
        {'help': self.module.CMDhelp}, self.sc.enumerate_commands())

  def testFindNearestCommand_ExactMatch(self):
    self.module.CMDfoo = object()
    self.assertEqual(
        self.module.CMDfoo, self.sc.find_nearest_command('foo'))

  def testFindNearestCommand_UniquePrefix(self):
    self.module.CMDfoo = object()
    self.module.CMDbar = object()
    self.module.CMDunique_prefix = object()
    self.assertEqual(
        self.module.CMDunique_prefix,
        self.sc.find_nearest_command('unique-pre'))

  def testFindNearestCommand_NonUniquePrefix(self):
    self.module.CMDprefix1 = object()
    self.module.CMDprefix2 = object()
    self.assertIsNone(self.sc.find_nearest_command('prefix'))

  def testFindNearestCommand_CloseEnough(self):
    self.module.CMDfoo = object()
    self.module.CMDbar = object()
    self.module.CMDclose_enough = object()
    self.assertEqual(
        self.module.CMDclose_enough,
        self.sc.find_nearest_command('clos-enough'))

  def testFindNearestCommand_TooManyCloseEnough(self):
    self.module.CMDcase_enough = object()
    self.module.CMDclose_enough = object()
    self.assertIsNone(self.sc.find_nearest_command('clase-enough'))

  def testFindNearestCommand_ClosestIsNotCloseEnough(self):
    self.module.CMDfoo = object()
    self.module.CMDbar = object()
    self.module.CMDnot_close_enough = object()
    self.assertIsNone(self.sc.find_nearest_command('clos-enof'))

  def testExecute(self):
    self.module.CMDfoo = mock.Mock(
        __doc__='foo documentation',
        __name__='CMDfoo',
        epilog='epilog',
        usage_more='usage more')

    self.sc.execute(self.parser, ['foo', '--bar', '--baz'])

    self.module.CMDfoo.assert_called_once_with(self.parser, ['--bar', '--baz'])

    self.assertEqual('foo documentation\n\n', self.parser.description)
    self.assertEqual('\nepilog\n', self.parser.epilog)
    self.parser.set_usage.assert_called_once_with(
        'usage: %prog foo [options] usage more')

  def testExecute_Help(self):
    self.module.CMDhelp = mock.Mock(
        __name__='CMDhelp',
        __doc__='help documentation',
        usage_more=None)
    self.module.CMDfoo = mock.Mock(
        __name__='CMDfoo',
        __doc__='foo documentation')
    self.module.CMDbar_baz = mock.Mock(
        __name__='CMDbar_baz',
        __doc__='bar-baz documentation')
    self.parser.parse_args.side_effect = [HelpException]

    self.sc.execute(self.parser, ['--help'])

    self.module.CMDhelp.assert_called_once_with(self.parser, [])

    self.assertEqual(
        'Module documentation\n\n'
        'Commands are:\n'
        '  bar-baz bar-baz documentation\n'
        '  foo     foo documentation\n'
        '  help    help documentation\n',
        self.parser.description)
    self.parser.set_usage.assert_called_once_with(
        'usage: %prog <command> [options]')

  def testExecute_CommandHelp(self):
    self.module.CMDhelp = mock.Mock(
        __name__='CMDhelp',
        __doc__='help documentation')
    self.module.CMDfoo = mock.Mock(
        __name__='CMDfoo',
        __doc__='foo documentation',
        epilog=None, usage_more=None)
    self.module.CMDbar_baz = mock.Mock(
        __name__='CMDbar_baz',
        __doc__='bar-baz documentation')
    self.parser.parse_args.side_effect = [HelpException]

    self.sc.execute(self.parser, ['help', 'foo'])

    self.module.CMDfoo.assert_called_once_with(self.parser, ['--help'])

    self.assertEqual('foo documentation\n\n', self.parser.description)
    self.parser.set_usage.assert_called_once_with('usage: %prog foo [options]')


if __name__ == '__main__':
  unittest.main()
