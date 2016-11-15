# Copyright (c) 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""gclient_eval - parsing and evaluating .gclient and DEPS files."""

import collections
import sys

import gclient_parser

class _PrintableOrderedDict(collections.OrderedDict):
  def __repr__(self, _repr_running=None):
    collections.OrderedDict.__repr__(self, {})


def Eval(obj, scope):
  """Evaluates the parsed AST obj using given the scope for variables."""

  tag = obj[0]
  if tag in ('bool', 'null', 'str', 'num'):
    return obj[1]
  if tag == 'object':
    o = _PrintableOrderedDict()
    for k, v in obj[1]:
      o[Eval(k, scope)] = Eval(v, scope)
    return o
  if tag == 'object_list':
    return [Eval(o, scope) for o in obj[1]]
  if tag == 'str_expr':
    s = ''
    for val in obj[1]:
      if val[0] == 'var':
        s += scope['vars'][val[1]]
      elif val[0] == 'str':
        s += val[1]
      elif val[0] == 'str_expr':
        s += Eval(val, scope)
      else:
        assert False, 'Unexpected AST tag: "%s"' % val[0]
    return s
  if tag == 'str_list':
    return [Eval(el, scope) for el in obj[1]]
  if tag == 'rec_list':
    # Convert recursedeps items into the format gclient expects: single
    # strings or tuples.
    return tuple(el[0] if el[1] == 'DEPS' else tuple(el) for el in obj[1])
  assert False, 'Unexpected AST tag: "%s"' % tag



class ParseFailure(Exception):
    pass


class CheckFailure(Exception):
  def __init__(self, msg, path, exp, act):
    super(CheckFailure, self).__init__(msg)
    self.path = path
    self.exp = exp
    self.act = act


def Check(content, path, expected_scope):
  parser = gclient_parser.Parser(content, path)
  ast, err = parser.parse()
  if err:
    raise ParseFailure(err)
  scope = {}
  for var, val in ast:
    scope[var] = Eval(val, scope)

  def fail(prefix, exp, act):
    raise CheckFailure('gclient check for %s:  %s exp %s, got %s' %
                       (path, prefix, repr(exp), repr(act)),
                       prefix, exp, act)

  def compare(expected, actual, var_path, actual_scope):
    if isinstance(expected, dict):
      exp = set(expected.keys())
      act = set(actual.keys())
      if exp != act:
        fail(var_path, exp, act)
      for k in expected:
        compare(expected[k], actual[k], var_path + '["%s"]' % k, actual_scope)
      return
    elif isinstance(expected, list):
      exp = len(expected)
      act = len(actual)
      if exp != act:
        fail('len(%s)' % var_path, expected_scope, actual_scope)
      for i in range(exp):
        compare(expected[i], actual[i], var_path + '[%d]' % i, actual_scope)
    else:
      if expected != actual:
        fail(var_path, expected_scope, actual_scope)

  compare(expected_scope, scope, '', scope)
