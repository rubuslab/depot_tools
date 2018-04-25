import parser as p
import tokenize


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
      'concat_string': p.OneOf([
          p.Sequence([
              p.OneOf([
                  ctx.g('base_string'),
                  ctx.g('var_string'),
              ]),
              p.t('+'),
              ctx.g('string'),
          ]),
          p.Sequence([
              p.t('('),
              p.OneOf([
                  ctx.g('base_string'),
                  ctx.g('var_string'),
              ]),
              ctx.g('string'),
              p.t(')'),
          ]),
      ]),
      'string': p.OneOf([
          ctx.g('concat_string'),
          ctx.g('base_string'),
          ctx.g('var_string'),
      ]),

      'list_entry': p.Sequence([
          p.OneOf([
              ctx.g('string'),
              ctx.g('dict'),
              ctx.g('tuple'),
          ]),
          p.Optional(p.t(',')),
      ]),
      'list': p.Sequence([
          p.t('['),
          p.Repeated(p.OneOf([
              ctx.g('comment'),
              ctx.g('list_entry'),
          ])),
          p.t(']'),
      ]),

      'tuple_entry': p.Sequence([ctx.g('string'), p.Optional(p.t(','))]),
      'tuple': p.Sequence([
          p.t('('),
          p.Repeated(p.OneOf([
              ctx.g('comment'),
              ctx.g('tuple_entry'),
          ])),
          p.t(')'),
      ]),

      'dict_entry': p.Sequence([
          ctx.g('string'),
          p.t(':'),
          p.OneOf([
              ctx.g('dict'),
              ctx.g('list'),
              ctx.g('string'),
              ctx.g('name'),
          ]),
          p.Optional(p.t(',')),
      ]),
      'dict': p.Sequence([
          p.t('{'),
          p.Repeated(p.OneOf([
              ctx.g('dict_entry'),
              ctx.g('comment'),
          ])),
          p.t('}'),
      ]),

      'assignment': p.Sequence([
          ctx.g('name'),
          p.t('='),
          p.OneOf([
              ctx.g('string'),
              ctx.g('list'),
              ctx.g('dict'),
          ]),
      ]),

      'top_level': p.Repeated(p.OneOf([
          ctx.g('comment'),
          ctx.g('assignment'),
      ]), fail_on_error=True),
  }

  return ctx
