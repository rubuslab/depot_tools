#!/usr/bin/env python
# Copyright (c) 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""A new implementation of gclient that supports conditionals."""

from __future__ import print_function

import argparse
import collections
import json
import os
import pprint
import sys
import traceback

from parser import Parser


def main(argv):
    return Commands().main(argv)


class Commands(object):
  def __init__(self):
      self._verbose = False

  def main(self, argv):
    args = self.parse_args(argv)
    return args.func(args)

  def parse_args(self, argv):
    parser = argparse.ArgumentParser()

    parser.add_argument('-v', '--verbose', action='store_true')
    subps = parser.add_subparsers()

    subp = subps.add_parser('lint', help='Validate the syntax of the files.')
    subp.add_argument('files', nargs='*', metavar='FILE')
    subp.set_defaults(func=self.run_lint)

    subp = subps.add_parser('help', help='Get help on a subcommand.')
    subp.add_argument(nargs='?', action='store', dest='subcommand',
        help='The command to get help for.')
    subp.set_defaults(func=self.run_help)

    subp = subps.add_parser('print',
        help='Parse the file and print the output as a Python dict')
    subp.add_argument('file', metavar='FILE')
    subp.set_defaults(func=self.run_print)

    return parser.parse_args(argv)

  def run_help(self, args):
    if args.subcommand:
        self.main([args.subcommand, '--help'])
    return self.main(['--help'])

  def run_lint(self, args):
    failed = False
    if args.files and args.files != ['-']:
      for f in args.files:
        try:
          with open(f) as fp:
            s = fp.read()
            scope, err = self.parse(f, s)
            if err:
              self.print_(err)
              failed = True
            else:
              self.print_(json.dumps(tree, indent=2))
        except Exception as e:
            self.print_('Failed to read %s: %s' % (f, e))
            failed = True
    else:
      s = sys.stdin.read()
      scope, err = self.parse('<stdin>', s)
      if err:
        self.print_(err)
        failed = True

    return 1 if failed else 0

  def run_print(self, args):
    try:
      with open(args.file) as fp:
        s = fp.read()
        scope, err = self.parse(args.file, s)
        if err:
          self.print_(err)
          return 1
        self.print_(pprint.pformat(scope))
        return 0
    except Exception as e:
      self.print_('Failed to read %s: %s' % (args.file, str(e)))
      self.print_(traceback.format_exc(e))
      return 1

  def parse(self, fname, s):
    parser = Parser(s, fname)
    ast, err = parser.parse()
    if err:
      return None, err

    scope = {}
    for var, val in ast:
      scope[var] = Eval(val, scope)
    return scope, None

  def print_(self, *args, **kwargs):
    print(*args, **kwargs)


class _PrintableOrderedDict(collections.OrderedDict):
  def __repr__(self):
    return super(collections.OrderedDict, self).__repr__()


def Eval(obj, scope):
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
    return tuple(el[0] if el[1] == 'DEPS' else el for el in obj[1])
  assert False, 'Unexpected AST tag: "%s"' % tag


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))

