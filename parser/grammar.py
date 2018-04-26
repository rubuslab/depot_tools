import parser as p
import tokenize


def _CommaSeparatedRule(l_rule, rule, comment, r_rule):
  """Parses sequences of comma-separated rules.

  Accepts the following grammar (with comments anywhere):
    l_rule (rule (,rule)* ,?)? r_rule

  It's meant to deal with lists, tuples and dicts, so it accepts:
    []
    [<value>]
    [<value>,]
    [<value>, ..., <value>]
    [<value>, ..., <value>,]
  """
  return p.Sequence([
      l_rule,
      p.Optional(p.Sequence([
          p.Repeated(comment),
          rule,
          p.Repeated(p.Sequence([
              p.t(','),
              p.Repeated(comment),
              rule,
          ], flatten=True), flatten=True),
          p.Optional(p.t(',')),
          p.Repeated(comment),
      ], flatten=True)),
      r_rule,
  ], flatten=True)


def GetPythonLikeContext():
  ctx = p.Context()
  ctx.grammar = {
      'comment': p.t(tokenize.COMMENT),
      'name': p.t(tokenize.NAME),

      'base_string': p.t(tokenize.STRING),
      'var_string': p.Sequence([
          p.t('Var'),
          p.t('('),
          ctx.g('base_string'),
          p.t(')'),
      ]),
      'string': p.Sequence([
          p.OneOf([
              ctx.g('base_string'),
              ctx.g('var_string'),
          ]),
          p.Repeated(p.Sequence([
              p.t('+'),
              p.OneOf([
                  ctx.g('base_string'),
                  ctx.g('var_string'),
              ]),
          ]), flatten=True),
      ], flatten=True),

      '_value': p.OneOf([
          ctx.g('string'),
          ctx.g('name'),
          ctx.g('list'),
          ctx.g('tuple'),
          ctx.g('dict'),
      ]),

      'list': _CommaSeparatedRule(
          p.t('['),
          ctx.g('_value'),
          ctx.g('comment'),
          p.t(']'),
      ),

      'tuple': _CommaSeparatedRule(
          p.t('('),
          ctx.g('_value'),
          ctx.g('comment'),
          p.t(')'),
      ),

      'dict_entry': p.Sequence([
          ctx.g('string'),
          p.t(':'),
          ctx.g('_value'),
      ]),
      'dict': _CommaSeparatedRule(
          p.t('{'),
          ctx.g('dict_entry'),
          ctx.g('comment'),
          p.t('}'),
      ),

      'assignment': p.Sequence([
          ctx.g('name'),
          p.t('='),
          ctx.g('_value'),
      ]),

      'start': p.Repeated(p.OneOf([
          ctx.g('comment'),
          ctx.g('assignment'),
      ]), fail_on_error=True),
  }

  ctx.transformations = {
      'name': lambda t: ('string', t[1]),
      'comment': lambda t: ('comment', t[1]),
      'base_string': lambda t: eval(t[1]),
      'var_string': lambda t: '{%s}' % t[0],
      'string': lambda ts: ('string', ''.join(ts)),
      'assignment': lambda ts: ('dict_entry', ts),
  }

  return ctx
