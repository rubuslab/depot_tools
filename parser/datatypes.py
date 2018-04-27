import collections
import util


class Token(object):
  def Format(self):
    raise NotImplemented

  def __str__(self):
    return '\n'.join(self.Format())

  __repr__ = __str__


class Comment(Token):
  def __init__(self, token=None, value=None):
    self.token = token
    self.value = (value or token[1]).splitlines()
    self.inline = util.IsInlineComment(self.token)

  def Format(self):
    return self.value


class Name(Token):
  def __init__(self, token=None, value=None):
    self.token = token
    self.value = value or token[1]

  def __eq__(self, other):
    return eval(self.value) == other

  def Format(self):
    return [self.value]


class String(Token):
  def __init__(self, token=None, value=None):
    self.token = token
    self.value = value or token[1]
    self.value = self.value.replace('\\', '\\\\')
    self.value = self.value.replace('\'', '\\\'')

  def __hash__(self):
    return hash(self.value)

  def __eq__(self, other):
    if isinstance(other, String):
      return self.value == other.value
    return self.value == other

  def Format(self):
    return ['\'' + self.value + '\'']


class List(collections.MutableSequence, Token):
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
    value = ToToken(value)
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
    value = ToToken(value)
    self.tokens.insert(self.values[index], value)
    self.values.insert(index, self.values[index])
    for i in range(index + 1, len(self.values)):
      self.values[i] += 1

  def Format(self):
    entries = []
    for token in self.tokens:
      if not isinstance(token, Comment):
        token_lines = token.Format()
        token_lines[-1] += ','
        entries.append(token_lines)
      elif token.inline:
        entries.insert(-1, token.Format())
      else:
        entries.append(token.Format())
    return ['['] + util.Indent(sum(entries, [])) + [']']


class Dict(collections.MutableMapping, Token):
  def __init__(self, tokens=None):
    self.tokens = tokens or []
    self.values = {}
    for pos, token in enumerate(tokens):
      if isinstance(token, Comment):
        continue
      assert len(token) == 2, str(token[0])
      key = token[0]
      if key in self.values:
        raise Exception('Duplicated key %s' % key)
      self.values[key] = pos

  def __getitem__(self, key):
    return self.tokens[self.values[key]][1]

  def __setitem__(self, key, value):
    value = ToToken(value)
    if key in self.values:
      self.tokens[self.values[key]][1] = value
    else:
      key = ToToken(key)
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
    entries = []
    for token in self.tokens:
      if not isinstance(token, Comment):
        entry_lines = token[1].Format()
        entry_lines[0] = '%s: %s' % (token[0].Format()[0], entry_lines[0])
        entry_lines[-1] += ','
        entries.append(entry_lines)
      elif token.inline:
        entries.insert(-1, token.Format())
      else:
        entries.append(token.Format())
    return ['{'] + util.Indent(sum(entries, [])) + ['}']


def ToToken(obj):
  if obj in (None, True, False):
    return Name(value=str(obj))
  if isinstance(obj, Token):
    return obj
  if isinstance(obj, str):
    return String(value=obj)
  if isinstance(obj, list) or isinstance(obj, tuple):
    return List([ToToken(item) for item in obj])
  if isinstance(obj, dict):
    return Dict([
        [ToToken(key), ToToken(value)]
        for key, value in obj.iteritems()
    ])
  return String(str(obj))


