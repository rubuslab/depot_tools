import collections
import grammar


class Value(object):
  def Format(self):
    raise NotImplemented

  def __str__(self):
    return '\n'.join(self.Format())


class Comment(object):
  def __init__(self, value):
    if value[0] != '#':
      value = '# ' + value.strip()
    self.value = value

  def Format(self):
    return [self.value]

  def __str__(self):
    return '\n'.join(self.Format())


class String(Value):
  def __init__(self, value):
    value = value.replace('\\', '\\\\')
    value = value.replace('\'', '\\\'')
    self.value = value

  def __hash__(self):
    return hash(self.value)

  def __eq__(self, other):
    if isinstance(other, String):
      return self.value == other.value
    return self.value == other

  def Format(self):
    return ['\'' + self.value + '\'']


class List(collections.MutableSequence, Value):
  def __init__(self, tokens=None):
    self.tokens = tokens or []
    self.values = [
        position
        for position, token in enumerate(tokens)
        if not isinstance(token, Comment)
    ]

  def __getitem__(self, index):
    return self.tokens[self.values[index]]

  def __setitem__(self, index, value):
    value = EnsureValue(value)
    self.tokens.append(value)
    self.values.append(len(self.tokens) - 1)

  def __delitem__(self, index):
    index = self.values[index]
    del self.values[index]
    del self.tokens[index]
    for i in range(index, len(self.values)):
      self.values[i] -= 1

  def __len__(self):
    return len(self.values)

  def insert(self, index, value):
    value = EnsureValue(value)
    self.tokens.insert(self.values[index], value)
    self.values.insert(index, self.values[index])
    for i in range(index + 1, len(self.values)):
      self.values[i] += 1

  def Format(self):
    answer = ['[']
    for token in self.tokens:
      token_lines = token.Format()
      token_lines[-1] += ','
      answer.extend(['  ' + line for line in token_lines])
    answer.append(']')
    return answer


class Dict(collections.MutableMapping, Value):
  def __init__(self, tokens=None):
    self.tokens = tokens or []
    self.values = {}
    for pos, token in enumerate(tokens):
      if isinstance(token, Comment):
        continue
      key = token[0]
      if key in self.values:
        raise Exception('Duplicated key %s' % key)
      self.values[key] = pos

  def __getitem__(self, key):
    return self.tokens[self.values[key]][1]

  def __setitem__(self, key, value):
    value = EnsureValue(value)
    if key in self.values:
      self.tokens[self.values[key]][1] = value
    else:
      key = EnsureValue(key)
      self.tokens.append([key, value])
      self.values[key] = len(self.tokens) - 1

  def __delitem__(self, key):
    del self.tokens[self.values[key]]
    key_pos = self.values[key]
    del self.values[key]
    for key, pos in self.values.iteritems():
      if pos >= key_pos:
        self.values[key] -= 1

  def __iter__(self):
    return iter(self.values)

  def __len__(self):
    return len(self.values)

  def Format(self):
    answer = ['{']
    for token in self.tokens:
      if isinstance(token, Comment):
        answer.append('  ' + ''.join(token.Format()))
      else:
        value_lines = token[1].Format()
        value_lines[-1] += ','
        lead_line = '  %s: %s' % (
            ''.join(token[0].Format()), value_lines[0])
        answer.append(lead_line)
        answer.extend(['  ' + line for line in value_lines[1:]])
    answer.append('}')
    return answer


def GetPythonContext():
  ctx = grammar.GetPythonLikeContext()
  ctx.transform = True
  ctx.transformations.update({
      'name': lambda t: String(t[1]),
      'comment': lambda t: Comment(t[1]),
      'string': lambda ts: String(''.join(ts)),
      'dict_entry': lambda ts: [ts],
      'assignment': lambda ts: ts,
      'dict': Dict,
      'list': List,
      'tuple': List,
      'start': Dict,
  })
  return ctx


def EnsureValue(obj):
  if isinstance(obj, Value):
    return obj
  if isinstance(obj, str):
    return String(obj)
  if isinstance(obj, list) or isinstance(obj, tuple):
    return List([EnsureValue(item) for item in obj])
  if isinstance(obj, dict):
    return Dict([
        [EnsureValue(key), EnsureValue(value)]
        for key, value in obj.iteritems()
    ])
  return String(str(obj))
