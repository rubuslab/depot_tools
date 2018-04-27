import datatypes as d
import parser as p
import tokenize


TO_TYPE_VALUE_PAIR = {
    'name': lambda t: ('name', t[1]),
    'none': lambda t: ('none', None),
    'true': lambda t: ('true', True),
    'false': lambda t: ('false', False),
    'comment': lambda t: ('comment', t[1]),
    '_base_string': lambda t: eval(t[1]),
    '_var_string': lambda t: '{%s}' % t[0],
    'string': lambda ts: ('string', ''.join(ts)),
}

TO_PYTHON_LIKE_OBJECTS = {
    'name': d.String,
    'none': d.Name,
    'true': d.Name,
    'false': d.Name,
    'comment': d.Comment,
    '_base_string': lambda t: eval(t[1]),
    '_var_string': lambda t: '{%s}' % t[0],
    'string': lambda ts: d.String(value=''.join(ts)),
    'dict_entry': lambda ts: ts,
    'assignment': lambda ts: ts,
    'dict': d.Dict,
    'list': d.List,
    'tuple': d.List,
    'start': d.Dict,
}


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
      p.Repeated(comment),
      p.Optional(p.Sequence([
          rule,
          p.Repeated(p.Sequence([
              p.t(','),
              p.Repeated(comment),
              rule,
          ])),
          p.Optional(p.t(',')),
      ])),
      p.Repeated(comment),
      r_rule,
  ])


def GetGrammar():
  ctx = p.Context()
  ctx.grammar = {
      'comment': p.t(tokenize.COMMENT, keep=True),
      'name': p.t(tokenize.NAME, keep=True),

      'none': p.t('None', keep=True),
      'true': p.t('True', keep=True),
      'false': p.t('False', keep=True),

      '_base_string': p.t(tokenize.STRING, keep=True),
      '_var_string': p.Sequence([
          p.t('Var'),
          p.t('('),
          ctx.g('_base_string'),
          p.t(')'),
      ]),
      'string': p.Sequence([
          p.OneOf([
              ctx.g('_base_string'),
              ctx.g('_var_string'),
          ]),
          p.Repeated(p.Sequence([
              p.t('+'),
              p.OneOf([
                  ctx.g('_base_string'),
                  ctx.g('_var_string'),
              ]),
          ])),
      ]),

      '_value': p.OneOf([
          ctx.g('none'),
          ctx.g('true'),
          ctx.g('false'),
          ctx.g('string'),
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

      'start': p.Sequence([
          p.Repeated(p.OneOf([
            ctx.g('comment'),
            ctx.g('assignment'),
          ])),
          p.t(0),
      ]),
  }

  return ctx
