# Copyright (c) 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""gclient2 - A reimplentation of gclient with conditionals support."""

import sys

from parser import Parser
from runner import main, Eval

__all__ = [
    'Check',
    'Eval',
    'Parser'
    'main',
]

def Check(content, path, expected_scope):
  parser = Parser(content, path)
  ast, err = parser.parse()
  if err:
    import pdb; pdb.set_trace()
    raise Exception(err)
  scope = {}
  for var, val in ast:
    scope[var] = Eval(val, scope)

  def fail(prefix, exp, act):
    import pdb; pdb.set_trace()
    raise Exception('gclient2 parse failure for %s:  %s exp %s, got %s' %
                    (path, prefix, repr(exp), repr(act)))

  def compare(expected, actual, var_path):
    if isinstance(expected, dict):
      exp = set(expected.keys())
      act = set(actual.keys())
      if exp != act:
        fail(var_path, exp, act)
      for k, v in expected:
        compare(expected[k], actual[k], var_path + '["%s"]' % k)
      return
    elif isinstance(expected, list):
      exp = len(expected)
      act = len(actual)
      if exp != act:
        fail('len(%s)' % var_path, exp, act)
      for i in range(exp):
        compare(expected[i], actual[i], var_path + '[%d]' % i)
    else:
      if expected != actual:
        fail(var_path, expected, actual)

    compare(expected_scope, scope)
