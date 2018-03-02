import ast
import cStringIO
import collections
import tokenize

from third_party import schema
from gclient_eval import _GCLIENT_HOOKS_SCHEMA, _gclient_eval, EvaluateCondition


def UglyHack(value, node):
  # Used so we can have something that behaves like value except it also has a
  # .node attribute
  class UglyClass(type(value)):
    pass
  ugly = UglyClass(value)
  ugly.node = node
  return ugly


def Dict(dict_schema):
  # Given an ast.Dict node, it will attepmt to convert all keys to strings,
  # without parsing the values, and enforce the given schema.
  dict_schema = schema.Schema(dict_schema)
  def _convert(node):
    assert isinstance(node, ast.Dict)
    assert all(isinstance(key, ast.Str) for key in node.keys)
    return dict_schema.validate({
        k.s: v
        for k, v in zip(node.keys, node.values)
    })
  return schema.Use(_convert)


def List(list_schema):
  # Given an ast.List node, it will attepmt to convert it the list of it's ast
  #  without parsing them, and enforce the given schema.
  list_schema = schema.Schema(list_schema)
  def _convert(node):
    assert isinstance(node, ast.List)
    return list_schema.validate([element for element in node.elts])
  return schema.Use(_convert)


def String(global_scope):
  # If the given ast node evaluates to a string, it returns the given string
  # with an extra .node attribute that contains the ast node.
  def _convert(node):
    value = _gclient_eval(node, global_scope)
    assert isinstance(value, basestring)
    # Or maybe return a tuple.
    return UglyHack(value, node)
  return schema.Use(_convert)


def Schema(global_scope, general_schema):
  # Will attempt to parse the given ast node and enforce the given schema.
  general_schema = schema.Schema(general_schema)
  def _convert(node):
    return general_schema.validate(_gclient_eval(node, global_scope))
  return schema.Use(_convert)


def _GCLIENT_DEPS_SCHEMA(global_scope):
  Str = String(global_scope)
  return Dict({
      schema.Optional(basestring): schema.Or(
          None,
          Str,
          Dict({
              'url': Str,
              schema.Optional('condition'): Str,
              schema.Optional('dep_type', default='git'): Str,
          }),
          Dict({
              'packages': List([
                  Dict({
                      'package': Str,
                      'version': Str,
                  })
              ]),
              schema.Optional('condition'): Str,
              schema.Optional('dep_type', default='cipd'): Str,
          }),
      )
  })


def _GCLIENT_SCHEMA(global_scope):
  # We want to "parse deeply" the ast  except for deps, for which we want
  # to store the ast node along with the value.
  S = lambda sch: Schema(global_scope, sch)
  return schema.Schema({
      # The tokens. Will be used to preserve formatting and comments.
      schema.Optional('tokens'): object,
      schema.Optional('allowed_hosts'): S([schema.Optional(basestring)]),
      schema.Optional('deps'): _GCLIENT_DEPS_SCHEMA(global_scope),
      schema.Optional('deps_os'): S({
          schema.Optional(basestring): _GCLIENT_DEPS_SCHEMA(global_scope),
      }),

      schema.Optional('gclient_gn_args_file'): S(basestring),

      schema.Optional('gclient_gn_args'): S([schema.Optional(basestring)]),

      schema.Optional('hooks'): S(_GCLIENT_HOOKS_SCHEMA),

      schema.Optional('hooks_os'): S({
          schema.Optional(basestring): _GCLIENT_HOOKS_SCHEMA
      }),

      schema.Optional('include_rules'): S([schema.Optional(basestring)]),

      schema.Optional('pre_deps_hooks'): S(_GCLIENT_HOOKS_SCHEMA),

      schema.Optional('recursion'): S(int),

      schema.Optional('recursedeps'): S([
          schema.Optional(schema.Or(
              basestring,
              (basestring, basestring),
              [basestring, basestring]
          )),
      ]),

      schema.Optional('skip_child_includes'): S([schema.Optional(basestring)]),

      schema.Optional('specific_include_rules'): S({
          schema.Optional(basestring): [basestring]
      }),

      schema.Optional('target_os'): S([schema.Optional(basestring)]),

      schema.Optional('use_relative_paths'): S(bool),

      schema.Optional('vars'): S({
          schema.Optional(basestring): schema.Or(basestring, bool),
      }),
  })


def Exec(content, global_scope, local_scope, filename='<unknown>'):
  # Map from position to (modifiable) token info.
  tokens = {
      token[2]: list(token)
      for token in tokenize.generate_tokens(
          cStringIO.StringIO(content).readline)
  }
  local_scope = {
      'tokens': tokens,
  }
  node_or_string = ast.parse(content, filename=filename, mode='exec')
  if isinstance(node_or_string, ast.Expression):
    node_or_string = node_or_string.body

  def _visit_in_module(node):
    if isinstance(node, ast.Assign):
      if len(node.targets) != 1:
        raise ValueError(
            'invalid assignment: use exactly one target (file %r, line %s)' % (
                filename, getattr(node, 'lineno', '<unknown>')))
      target = node.targets[0]
      if not isinstance(target, ast.Name):
        raise ValueError(
            'invalid assignment: target should be a name (file %r, line %s)' % (
                filename, getattr(node, 'lineno', '<unknown>')))
      if target.id in local_scope:
        raise ValueError(
            'invalid assignment: overrides var %r (file %r, line %s)' % (
                target.id, filename, getattr(node, 'lineno', '<unknown>')))

      local_scope[target.id] = node.value
    else:
      raise ValueError(
          'unexpected AST node: %s %s (file %r, line %s)' % (
              node, ast.dump(node), filename,
              getattr(node, 'lineno', '<unknown>')))

  if isinstance(node_or_string, ast.Module):
    for stmt in node_or_string.body:
      _visit_in_module(stmt)
  else:
    raise ValueError(
        'unexpected AST node: %s %s (file %r, line %s)' % (
            node_or_string,
            ast.dump(node_or_string),
            filename,
            getattr(node_or_string, 'lineno', '<unknown>')))

  return _GCLIENT_SCHEMA(global_scope).validate(local_scope)


def WriteToFile(gclient_dict, filename):
  assert 'tokens' in gclient_dict
  contents = sorted(gclient_dict['tokens'].values(), key=lambda token: token[2])
  print [c for c in contents if len(c) != 5]

  with open(filename, 'w') as f:
    f.write(tokenize.untokenize(contents))


def EditRevision(gclient_dict, dep_name, new_revision):
  assert 'tokens' in gclient_dict

  tokens = gclient_dict['tokens']
  dep = gclient_dict['deps'][dep_name]
  if isinstance(dep, dict):
    dep = dep['url']

  node = dep.node
  if isinstance(node, ast.BinOp):
    node = node.right
  # We're not dealing with Vars yet.
  assert isinstance(node, ast.Str)

  position = node.lineno, node.col_offset
  tokens[position][1] = repr(new_revision)
  node.s = new_revision

  ugly = UglyHack(new_revision, dep.node)
  if isinstance(dep, dict):
    gclient_dict['deps'][dep_name]['url'] = ugly
  else:
    gclient_dict['deps'][dep_name] = ugly



def main():
  with open("DEPS") as f:
    contents = f.read()

  local_scope = {}
  global_scope = {
      'Var': lambda x: '{%s}' % x,
      'deps_os': {},
  }
  local_scope = Exec(contents, global_scope, local_scope)

  EditRevision(local_scope, 'src/third_party/libevdev/src', 'deadbeef')
  EditRevision(local_scope, 'src/third_party/libjpeg_turbo', 'lemur_rev')

  print local_scope['deps']['src/third_party/libevdev/src']
  print local_scope['deps']['src/third_party/libjpeg_turbo']

  WriteToFile(local_scope, "DEPS2")

main()
