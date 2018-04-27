import collections
import cStringIO
import datatypes as d
import grammar
import pprint
import sys
import tokenize
import util


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
    test = open("../../../webrtc/src/DEPS").read()
  else:
    test = open(sys.argv[1]).read()

  result = Parse(test)
  if result.err:
    print '\n'.join(result.err_msg)
  else:
    result = result.value
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
