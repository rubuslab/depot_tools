import cStringIO
import pprint
import token
import tokenize


class Context(object):
  def __init__(self):
    self.grammar = {}
    self.transform = False
    self.transformers = {}

  def g(self, rule):
    def Parse(stack, tokens, index):
      parsed, index, err = self.grammar[rule](stack + [rule], tokens, index)
      if rule[0] != '_' and not err:
        if self.transform and rule in self.transformers:
          parsed = self.transformers[rule](parsed)
        else:
          parsed = (rule, parsed)
      return parsed, index, err
    return Parse


def GenerateTokens(contents):
  return [
      tok
      for tok in tokenize.generate_tokens(
          cStringIO.StringIO(contents).readline)
      if tok[0] not in {token.NEWLINE, tokenize.NL}
  ]

def Error(msg, token, stack):
  message = 'Error parsing %s ([%s] %s) at %s:\n%s\nStack trace:\n\t%s\n' % (
      token[1],
      token[0],
      tokenize.tok_name[token[0]],
      token[2],
      msg,
      '\n\t'.join(stack))
  return None, None, message.splitlines()

def t(tok):
  def Parse(stack, tokens, index):
    tok_name = None
    if isinstance(tok, int):
      if tokens[index][0] == tok:
        return tokens[index], index + 1, None
      tok_name = tokenize.tok_name[tok]
    if isinstance(tok, str):
      if tokens[index][1] == tok:
        return None, index + 1, None
      tok_name = tok
    return Error('Expected %s' % tok_name, tokens[index], stack)
  return Parse

def Repeated(rule, fail_on_error=False):
  def Parse(stack, tokens, index):
    result = []
    while not token.ISEOF(tokens[index][0]):
      parsed, next_index, err = rule(stack, tokens, index)
      if err:
        if fail_on_error:
          return parsed, next_index, err
        return result, index, None
      index = next_index
      if parsed:
        result.append(parsed)
    return result, index, None
  return Parse

def OneOf(rules):
  def Parse(stack, tokens, index):
    errors = []
    for rule in rules:
      parsed, next_index, err = rule(stack, tokens, index)
      if err:
        errors.extend(err + [''])
      elif parsed:
        return parsed, next_index, err
    return Error('All options returned errors:\n\t%s' % '\n\t'.join(errors),
                 tokens[index], stack)
  return Parse

def Sequence(rules):
  def Parse(stack, tokens, index):
    result = []
    for rule in rules:
      parsed, index, err = rule(stack, tokens, index)
      if parsed:
        result.append(parsed)
      if err:
        return parsed, index, err
    return result, index, None
  return Parse

ctx = Context()
ctx.grammar = {
    'comment': t(tokenize.COMMENT),
    'string': t(token.STRING),
    'name': t(token.NAME),

    'list_entry': OneOf([
        Sequence([ctx.g('string'), t(',')]),
        Sequence([ctx.g('dict'), t(',')]),
    ]),
    'list': Sequence([
        t('['),
        Repeated(OneOf([
            ctx.g('comment'),
            ctx.g('list_entry'),
        ])),
        t(']'),
    ]),

    'dict_entry': Sequence([
        ctx.g('string'),
        t(':'),
        OneOf([
            ctx.g('list'),
            ctx.g('string'),
            ctx.g('dict'),
            t('None'),
        ]),
        t(','),
    ]),
    'dict': Sequence([
        t('{'),
        Repeated(OneOf([
            ctx.g('comment'),
            ctx.g('dict_entry'),
        ])),
        t('}'),
    ]),

    'assignment': Sequence([
        ctx.g('name'),
        t('='),
        OneOf([
            ctx.g('string'),
            ctx.g('list'),
            ctx.g('dict'),
        ]),
    ]),

    'top_level': Repeated(OneOf([
        ctx.g('comment'),
        ctx.g('assignment'),
    ]), fail_on_error=True),
}
ctx.transform = True

def Dict(tokens):
  return dict(token[1] for token in tokens if token[0] == 'dict_entry')

def List(tokens):
  return list(token[1] for token in tokens if token[0] == 'list_entry')

ctx.transformers = {
    'name': lambda t: t[1],
    'string': lambda t: eval(t[1]),
    'top_level': lambda ts: Dict(ts),
    'assignment': lambda ts: ('dict_entry', [ts[0], ts[1]]),
    'dict': lambda ts: Dict(ts[0]),
    'list': lambda ts: List(ts[0]),
}


test = """\
# Big
# Block
# Of
# Copyright

deps = {
  'src/v8': {
    'url': '{chromium_git}/v8/v8.git',
    'revision': '{v8_revision}',
  },
  # Some comment on src-internal
  'src-internal': {
    'url': 'https://chrome-internal.googlesource.com/src',
    'revision': 'fake_revision',
    'condition': 'checkout_ios',
  },
  'src/something': {
    'packages': [
      {
        # Some comment on fake_package
        'package': 'fake_package',
        'version': 'version:3.0',
      },
    ],
    'condition': 'checkout_android',
  },
}

vars = {
  # Some comment
  'chromium_git': 'https://chromium.googlesource.com',
  'v8_revision': 'deadbeef',
}
"""

result, index, err = ctx.g('top_level')([], GenerateTokens(test), 0)
if err:
  print '\n'.join(err)
else:
  pprint.pprint(result)
