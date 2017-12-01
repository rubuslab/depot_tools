#!/usr/bin/env python
# coding=utf8
# Copyright (c) 2011 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Unit tests for fix_encoding.py."""

import os
import subprocess
import sys
import tempfile
import unittest

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

sys.path.insert(0, ROOT_DIR)

import fix_encoding


# \U0001f310  U+1F310  utf-8: \xf0\x9f\x8c\x90
PRINT_EMOJI = (
  'import fix_encoding,sys;print fix_encoding.fix_encoding();'
  'print "\\xf0\\x9f\\x8c\\x90".decode("utf-8");'
  'print "\xff"'
  )

class FixEncodingTest(unittest.TestCase):
  # Nice mix of latin, hebrew, arabic and chinese. Doesn't mean anything.
  text = u'Héllô 偉大 سيد🌐'

  def test_code_page(self):
    # Make sure printing garbage won't throw.
    print self.text.encode() + '\xff'
    print >> sys.stderr, self.text.encode() + '\xff'

  def test_utf8(self):
    # Make sure printing utf-8 works.
    print self.text.encode('utf-8')
    print >> sys.stderr, self.text.encode('utf-8')

  def test_unicode(self):
    # Make sure printing unicode works.
    print self.text
    print >> sys.stderr, self.text

  def test_default_encoding(self):
    self.assertEquals('utf-8', sys.getdefaultencoding())

  def test_win_console(self):
    if sys.platform != 'win32':
      return
    # This should fail if not redirected, e.g. run directly instead of through
    # the presubmit check. Can be checked with:
    # python tests\fix_encoding_test.py
    self.assertEquals(
        sys.stdout.__class__, fix_encoding.WinUnicodeOutput)
    self.assertEquals(
        sys.stderr.__class__, fix_encoding.WinUnicodeOutput)
    self.assertEquals(sys.stdout.encoding, sys.getdefaultencoding())
    self.assertEquals(sys.stderr.encoding, sys.getdefaultencoding())

  def test_multiple_calls(self):
    # Shouldn't do anything.
    self.assertEquals(False, fix_encoding.fix_encoding())

  def _run(self, cmd, env):
    out = subprocess.check_output(cmd, cwd=ROOT_DIR, env=env)
    self.assertEqual(u'True\n\U0001f310\n'.encode('utf-8') + '\xff\n', out)
    self.assertEqual(u'True\n🌐\n'.encode('utf-8') + '\xff\n', out)

  def _run_as_arg(self, env):
    # When testing on the infrastructure, the current directory may not be in
    # PYTHONPATH.
    env['PYTHONPATH'] = os.pathsep.join((ROOT_DIR, env.get('PYTHONPATH') or ''))
    self._run([sys.executable, '-c', PRINT_EMOJI], env)

  def _run_tmp_file(self, env):
    h, tmp = tempfile.mkstemp(prefix='fix_encoding_test', suffix='.py')
    os.write(h, '# coding=utf-8\n')
    os.write(h, PRINT_EMOJI + '\n')
    os.close(h)
    try:
      self._run([sys.executable, tmp], env)
    finally:
      os.remove(tmp)

  def test_lang_default(self):
    self._run_as_arg(os.environ.copy())

  def test_lang_unset(self):
    env = os.environ.copy()
    env.pop('LANG', None)
    env.pop('LANGUAGE', None)
    self._run_as_arg(env)

  def test_lang_empty(self):
    env = os.environ.copy()
    env['LANG'] = ''
    env['LANGUAGE'] = ''
    self._run_as_arg(env)

  def test_lang_C(self):
    env = os.environ.copy()
    env['LANG'] = 'C.UTF-8'
    env['LANGUAGE'] = 'C.UTF-8'
    self._run_as_arg(env)

  def test_lang_bad(self):
    env = os.environ.copy()
    env['LANG'] = 'C.ASCII'
    env['LANGUAGE'] = 'C.ASCII'
    self._run_as_arg(env)

  def test_script_lang_default(self):
    self._run_tmp_file(os.environ.copy())

  def test_script_lang_unset(self):
    env = os.environ.copy()
    env.pop('LANG', None)
    env.pop('LANGUAGE', None)
    self._run_tmp_file(env)

  def test_script_lang_empty(self):
    env = os.environ.copy()
    env['LANG'] = ''
    env['LANGUAGE'] = ''
    self._run_tmp_file(env)

  def test_script_lang_C(self):
    env = os.environ.copy()
    env['LANG'] = 'C.UTF-8'
    env['LANGUAGE'] = 'C.UTF-8'
    self._run_tmp_file(env)

  def test_script_lang_bad(self):
    env = os.environ.copy()
    env['LANG'] = 'C.ASCII'
    env['LANGUAGE'] = 'C.ASCII'
    self._run_tmp_file(env)


if __name__ == '__main__':
  assert fix_encoding.fix_encoding()
  unittest.main()
