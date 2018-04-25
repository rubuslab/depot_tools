import parser as p
import tokenize


def CommaSeparatedRule(l_rule, rule, comment, r_rule):
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
              ctx.g('string'),
          ]), flatten=True),
      ], flatten=True),

      'value': p.OneOf([
          ctx.g('string'),
          ctx.g('name'),
          ctx.g('list'),
          ctx.g('tuple'),
          ctx.g('dict'),
      ]),

      'list': CommaSeparatedRule(
          p.t('['),
          ctx.g('value'),
          ctx.g('comment'),
          p.t(']'),
      ),

      'tuple': CommaSeparatedRule(
          p.t('('),
          ctx.g('value'),
          ctx.g('comment'),
          p.t(')'),
      ),

      'dict_entry': p.Sequence([
          ctx.g('string'),
          p.t(':'),
          ctx.g('value'),
      ]),
      'dict': CommaSeparatedRule(
          p.t('{'),
          ctx.g('dict_entry'),
          ctx.g('comment'),
          p.t('}'),
      ),

      'assignment': p.Sequence([
          ctx.g('name'),
          p.t('='),
          ctx.g('value'),
      ]),

      'top_level': p.Repeated(p.OneOf([
          ctx.g('comment'),
          ctx.g('assignment'),
      ]), fail_on_error=True),
  }

  return ctx
