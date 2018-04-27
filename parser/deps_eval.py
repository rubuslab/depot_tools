import collections
import cStringIO
import datatypes as d
import grammar
import pprint
import sys
import tokenize
import util

sys.path.insert(0, '..')
from third_party import schema


class DepsDict(d.Dict):
  def Format(self):
    answer = []
    for token in self.tokens:
      if isinstance(token, d.Comment):
        answer.append(''.join(token.Format()))
      else:
        entry_lines = token[1].Format()
        entry_lines[0] = '%s = %s' % (token[0].value, entry_lines[0])
        answer.extend(entry_lines)
    return answer


def v(s):
  def validate(x):
    try:
      x = type(s)(x)
    except:
      return False
    schema.Schema(s).validate(x)
    return True
  return validate

_GCLIENT_DEPS_SCHEMA = v({
    schema.Optional(d.String): schema.Or(
        None,
        d.String,
        v({
            'url': schema.Or(None, d.String),
            schema.Optional('condition'): d.String,
            schema.Optional('dep_type', default='git'): d.String,
        }),
        v({
            'packages': v([
                v({
                    'package': d.String,
                    'version': d.String,
                }),
              ]),
            schema.Optional('condition'): d.String,
            schema.Optional('dep_type', default='git'): d.String,
        }),
    ),
})

_GCLIENT_HOOKS_SCHEMA = v([v({
    # Hook action: list of command-line arguments to invoke.
    'action': v([d.String]),

    # Name of the hook. Doesn't affect operation.
    schema.Optional('name'): d.String,

    # Hook pattern (regex). Originally intended to limit some hooks to run
    # only when files matching the pattern have changed. In practice, with git,
    # gclient runs all the hooks regardless of this field.
    schema.Optional('pattern'): d.String,

    # Working directory where to execute the hook.
    schema.Optional('cwd'): d.String,

    # Optional condition string. The hook will only be run
    # if the condition evaluates to True.
    schema.Optional('condition'): d.String,
})])

_GCLIENT_SCHEMA = schema.Schema(v({
    # List of host names from which dependencies are allowed (whitelist).
    # NOTE: when not present, all hosts are allowed.
    # NOTE: scoped to current DEPS file, not recursive.
    schema.Optional('allowed_hosts'): v([schema.Optional(d.String)]),

    # Mapping from paths to repo and revision to check out under that path.
    # Applying this mapping to the on-disk checkout is the main purpose
    # of gclient, and also why the config file is called DEPS.
    #
    # The following functions are allowed:
    #
    #   Var(): allows variable substitution (either from 'vars' dict below,
    #          or command-line override)
    schema.Optional('deps'): _GCLIENT_DEPS_SCHEMA,

    # Similar to 'deps' (see above) - also keyed by OS (e.g. 'linux').
    # Also see 'target_os'.
    schema.Optional('deps_os'): v({
        schema.Optional(d.String): _GCLIENT_DEPS_SCHEMA,
    }),

    # Path to GN args file to write selected variables.
    schema.Optional('gclient_gn_args_file'): d.String,

    # Subset of variables to write to the GN args file (see above).
    schema.Optional('gclient_gn_args'): v([schema.Optional(d.String)]),

    # Hooks executed after gclient sync (unless suppressed), or explicitly
    # on gclient hooks. See _GCLIENT_HOOKS_SCHEMA for details.
    # Also see 'pre_deps_hooks'.
    schema.Optional('hooks'): _GCLIENT_HOOKS_SCHEMA,

    # Similar to 'hooks', also keyed by OS.
    schema.Optional('hooks_os'): v({
        schema.Optional(d.String): _GCLIENT_HOOKS_SCHEMA
    }),

    # Rules which #includes are allowed in the directory.
    # Also see 'skip_child_includes' and 'specific_include_rules'.
    schema.Optional('include_rules'): v([schema.Optional(d.String)]),

    # Hooks executed before processing DEPS. See 'hooks' for more details.
    schema.Optional('pre_deps_hooks'): _GCLIENT_HOOKS_SCHEMA,

    # Recursion limit for nested DEPS.
    schema.Optional('recursion'): int,

    # Whitelists deps for which recursion should be enabled.
    schema.Optional('recursedeps'): v([
        schema.Optional(schema.Or(
            d.String,
            v((d.String, d.String)),
            v([d.String, d.String])
        )),
    ]),

    # Blacklists directories for checking 'include_rules'.
    schema.Optional('skip_child_includes'): v([schema.Optional(d.String)]),

    # Mapping from paths to include rules specific for that path.
    # See 'include_rules' for more details.
    schema.Optional('specific_include_rules'): v({
        schema.Optional(d.String): v([d.String])
    }),

    # List of additional OS names to consider when selecting dependencies
    # from deps_os.
    schema.Optional('target_os'): v([schema.Optional(d.String)]),

    # For recursed-upon sub-dependencies, check out their own dependencies
    # relative to the paren't path, rather than relative to the .gclient file.
    schema.Optional('use_relative_paths'): schema.Or(True, False),

    # Variables that can be referenced using Var() - see 'deps'.
    schema.Optional('vars'): v({
        schema.Optional(d.String): schema.Or(d.String, schema.Or(True, False)),
    }),
}))


def _GenerateTokens(contents):
  tokens = []
  last_was_comment = False
  for token in tokenize.generate_tokens(cStringIO.StringIO(contents).readline):
    if token[0] == tokenize.COMMENT and last_was_comment:
      tokens[-1][1] += '\n' + token[1]
    elif token[0] not in (tokenize.NEWLINE, tokenize.NL):
      tokens.append(list(token))
    last_was_comment = token[0] == tokenize.COMMENT and not util.IsInlineComment(token)
  return tokens


def Parse(contents):
  ctx = grammar.GetGrammar()
  ctx.transformations = grammar.TO_PYTHON_LIKE_OBJECTS
  ctx.transformations['start'] = DepsDict

  tokens = _GenerateTokens(contents)
  return ctx.Parse(tokens)


def FormatDep(parent, dep_name, dep):
  if isinstance(dep, d.String):
    origin, _, revision = dep.value.partition('@')
    revision = revision or None
    parent[dep_name] = {
        'url': origin,
        'revision': revision,
    }
  elif 'url' in dep and 'revision' not in dep:
    origin, _, revision = dep['url'].value.partition('@')
    revision = revision or None
    dep['url'] = origin
    dep['revision'] = revision

def main():
  if len(sys.argv) < 2:
    test = open("../../../chromium/src/DEPS").read()
  else:
    test = open(sys.argv[1]).read()

  result = Parse(test)
  if result.err:
    print '\n'.join(result.err_msg)
  else:
    result = result.value
    result = _GCLIENT_SCHEMA.validate(result)

    if 'deps' in result:
      for dep_name, dep in result['deps'].iteritems():
        FormatDep(result['deps'], dep_name, dep)

    if 'deps_os' in result:
      result.setdefault('deps', {})
      for os_name, deps_os in result['deps_os'].iteritems():
        condition_name = 'checkout_' + os_name.value
        for dep_name, dep in deps_os.iteritems():
          if dep_name not in result['deps']:
            result['deps'][dep_name] = dep
            FormatDep(result['deps'], dep_name, dep)
      del result['deps_os']

    if 'recursedeps' in result:
      for recursedeps in result['recursedeps']:
        if isinstance(recursedeps, d.String):
          result['deps'][recursedeps]['recurse'] = 'DEPS'
        else:
          result['deps'][recursedeps[0]]['recurse'] = recursedeps[1]
      del result['recursedeps']

    print result


if __name__ == '__main__':
  sys.exit(main())
