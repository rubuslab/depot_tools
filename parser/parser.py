import tokenize


class Context(object):
  def __init__(self):
    self.grammar = {}
    self.transform = False
    self.transformers = {}
    self.max_depth = 100

  def GrammarRule(self, rule):
    def Parse(stack, tokens, index):
      if len(stack) > self.max_depth:
        return Error('Max depth exceeded: %s' % len(stack), tokens[index], stack)
      parsed, index, err = self.grammar[rule](stack + [rule], tokens, index)
      if not err:
        if self.transform and rule in self.transformers:
          parsed = self.transformers[rule](parsed)
        elif rule[0] != '_':
          parsed = (rule, parsed)
      return parsed, index, err
    return Parse

  g = GrammarRule


def Error(msg, token, stack):
  message = 'Error parsing %s ([%s] %s) as %s at %s:\n%s\nStack trace:\n\t%s\n' % (
      token[1],
      token[0],
      tokenize.tok_name[token[0]],
      stack[-1],
      token[2],
      msg,
      '\n\t'.join(stack))
  return None, None, message.splitlines()


def Terminal(tok):
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

t = Terminal


def Repeated(rule, fail_on_error=False):
  def Parse(stack, tokens, index):
    result = []
    while not tokenize.ISEOF(tokens[index][0]):
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


def Optional(rule):
  def Parse(stack, tokens, index):
    parsed, next_index, err = rule(stack, tokens, index)
    if err:
      return None, index, None
    return parsed, next_index, err
  return Parse
