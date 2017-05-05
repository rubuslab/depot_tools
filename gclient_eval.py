# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import ast


def _gclient_eval(node_or_string, global_scope, filename='<unknown>'):
  _safe_names = {'None': None, 'True': True, 'False': False}
  if isinstance(node_or_string, basestring):
    node_or_string = ast.parse(node_or_string, filename=filename, mode='eval')
  if isinstance(node_or_string, ast.Expression):
    node_or_string = node_or_string.body
  def _convert(node):
    if isinstance(node, ast.Str):
      return node.s
    elif isinstance(node, ast.Tuple):
      return tuple(map(_convert, node.elts))
    elif isinstance(node, ast.List):
      return list(map(_convert, node.elts))
    elif isinstance(node, ast.Dict):
      return dict((_convert(k), _convert(v))
                  for k, v in zip(node.keys, node.values))
    elif isinstance(node, ast.Name):
      if node.id in _safe_names:
        return _safe_names[node.id]
    elif isinstance(node, ast.Call):
      if not isinstance(node.func, ast.Name):
        raise ValueError('invalid call: func should be a name (file %r, line %s)' % (filename, getattr(node, 'lineno', '<unknown>')))
      if node.keywords or node.starargs or node.kwargs:
        raise ValueError('invalid call: only regular args are supported (file %r, line %s)' % (filename, getattr(node, 'lineno', '<unknown>')))
      args = map(_convert, node.args)
      return global_scope[node.func.id](*args)
    elif isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
      return _convert(node.left) + _convert(node.right)
    else:
      raise ValueError('unexpected AST node: %s (file %r, line %s)' % (node, filename, getattr(node, 'lineno', '<unknown>')))
  return _convert(node_or_string)


def _gclient_exec(node_or_string, global_scope, filename='<unknown>'):
  if isinstance(node_or_string, basestring):
    node_or_string = ast.parse(node_or_string, filename=filename, mode='exec')
  if isinstance(node_or_string, ast.Expression):
    node_or_string = node_or_string.body

  def _visit_in_module(node):
    if isinstance(node, ast.Assign):
      if len(node.targets) != 1:
        raise ValueError('invalid assignment: should have exactly one target (file %r, line %s)' % (filename, getattr(node, 'lineno', '<unknown>')))
      target = node.targets[0]
      if not isinstance(target, ast.Name):
        raise ValueError('invalid assignment: target should be a name (file %r, line %s)' % (filename, getattr(node, 'lineno', '<unknown>')))
      value = _gclient_eval(node.value, global_scope, filename=filename)
    else:
      raise ValueError('unexpected AST node: %s (file %r, line %s)' % (node, filename, getattr(node, 'lineno', '<unknown>')))

  def _visit_toplevel(node):
    if isinstance(node, ast.Module):
      for stmt in node.body:
        _visit_in_module(stmt)
    else:
      raise ValueError('unexpected AST node: %s (file %r, line %s)' % (node, filename, getattr(node, 'lineno', '<unknown>')))
  _visit_toplevel(node_or_string)


def Check(content, path, global_scope, expected_scope):
  _gclient_exec(content, global_scope, filename=path)
