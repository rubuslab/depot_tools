import tokenize
import util


class ParseResult(object):
  def __init__(self, value, next_index, keep=True, is_list=False, err=False,
               err_msg=None):
    self.value = value
    self.next_index = next_index
    self.keep = keep
    self.is_list = is_list
    self.err = err
    self.err_msg = err_msg or []


def ParseError(current_rule, current_parser, token, msg):
  err_msg = [
      'E %s:%s : When parsing "%s" (%s) at position %s' % (
          current_rule,
          current_parser,
          token[1],
          tokenize.tok_name[token[0]],
          token[2],
      )
  ] + msg
  return ParseResult(None, None, err=True, err_msg=err_msg)


class Parser(object):
  def name(self):
    return type(self).__name__

  def __call__(self, current_rule, tokens, index):
    raise NotImplemented


class Terminal(Parser):
  def __init__(self, token, keep=False):
    self.keep = keep
    self.token = token
    if isinstance(token, str):
      self.index = 1
      self.token_name = token
    else:
      self.index = 0
      self.token_name = tokenize.tok_name[token]

  def __call__(self, current_rule, tokens, index):
    if tokens[index][self.index] == self.token:
      return ParseResult(tokens[index], index + 1, keep=self.keep)
    return ParseError(current_rule, self.name(), tokens[index],
                      ['Expected %s' % self.token_name])

t = Terminal


class Optional(Parser):
  def __init__(self, parser):
    self.parser = parser

  def __call__(self, current_rule, tokens, index):
    result = self.parser(current_rule, tokens, index)
    if result.err:
      return ParseResult(None, index, keep=False, err_msg=result.err_msg)
    return result


class Repeated(Parser):
  def __init__(self, parser):
    self.parser = parser

  def __call__(self, current_rule, tokens, index):
    value = []
    last_err_msg = None
    while not tokenize.ISEOF(tokens[index][0]):
      result = self.parser(current_rule, tokens, index)
      if result.err:
        return ParseResult(value, index, err_msg=result.err_msg, is_list=True)
      index = result.next_index
      if result.keep:
        if result.is_list:
          value.extend(result.value)
        else:
          value.append(result.value)
    return ParseResult(value, index, is_list=True)


class OneOf(Parser):
  def __init__(self, parsers):
    self.parsers = parsers

  def __call__(self, current_rule, tokens, index):
    errors = []
    for parser in self.parsers:
      result = parser(current_rule, tokens, index)
      if result.err:
        errors.extend([''] + util.Indent(result.err_msg))
      else:
        return result
    return ParseError(current_rule, self.name(), tokens[index],
                      ['All options returned errors:'] + errors)


class Sequence(Parser):
  def __init__(self, parsers):
    self.parsers = parsers

  def __call__(self, current_rule, tokens, index):
    value = []
    original_index = index

    result = None
    for i, parser in enumerate(self.parsers):
      last_result = result
      result = parser(current_rule, tokens, index)
      index = result.next_index
      if result.err:
        if last_result and self.parsers[i-1].name() in {'Optional', 'Repeated'}:
          result.err_msg.extend([
              '',
              '  Next-to-last rule failed with:',
          ])
          result.err_msg.extend(util.Indent(last_result.err_msg))
        return result
      if result.keep:
        if result.is_list:
          value.extend(result.value)
        else:
          value.append(result.value)

    return ParseResult(value, index, is_list=True)


class GrammarParser(Parser):
  def __init__(self, ctx, rule_name):
    self.ctx = ctx
    self.rule_name = rule_name
    self.initialized = False
    if self.rule_name[0] != '_':
      self.transform = lambda result: (self.rule_name, result)
    else:
      self.transform = lambda result: result

  def initialize(self):
    self.initialized = True
    self.parser = self.ctx.grammar[self.rule_name]
    if self.rule_name in self.ctx.transformations:
      self.transform = self.ctx.transformations[self.rule_name]

  def __call__(self, current_rule, tokens, index):
    if not self.initialized:
      self.initialize()
    result = self.parser(self.rule_name, tokens, index)
    if not result.err:
      result.is_list = False
      result.value = self.transform(result.value)
    return result


class Context(object):
  def __init__(self):
    self.grammar = {}
    self.transformations = {}

  def g(self, rule):
    return GrammarParser(self, rule)

  def Parse(self, tokens):
    return self.g('start')('start', tokens, 0)
