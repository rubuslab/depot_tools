import cStringIO
import grammar
import pprint
import tokenize


def GenerateTokens(contents):
  return [
      token
      for token in tokenize.generate_tokens(
          cStringIO.StringIO(contents).readline)
      if token[0] not in {tokenize.NEWLINE, tokenize.NL}
  ]


ctx = grammar.GetPythonLikeContext()
ctx.transform = True

def Dict(tokens):
  # print "Dict"
  # print pprint.pprint(tokens)
  return {
      token[1][0]: token[1][1][1]
      for token in tokens
      if token[0] == 'dict_entry'
  }

def List(tokens):
  # print "List", tokens
  return list(token[1] for token in tokens if token[0] == 'value')

ctx.transformers = {
    'name': lambda t: t[1],
    'base_string': lambda t: eval(t[1]),
    'var_string': lambda t: '{%s}' % t[0],
    'string': lambda ts: ''.join(ts),
    'top_level': lambda ts: Dict(ts),
    'assignment': lambda ts: ('dict_entry', ts),
    'dict': lambda ts: Dict(ts),
    'list': lambda ts: List(ts),
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
  'src/webrtc': Var('webrtc_git') + '/src.git' + '@' + 'some_revision',
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

test = """\
deps = {
  "hola": Var("hello") + "world",
  # hello
  # world
  "mundo": "world",
  # lemur
}
"""

test = open("../../../src-internal/src-internal/DEPS").read()

result, index, err = ctx.g('top_level')([], GenerateTokens(test), 0)
if err:
  print '\n'.join(err)
else:
  pprint.pprint(result)
