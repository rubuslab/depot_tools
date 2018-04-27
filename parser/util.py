import tokenize


def Indent(lines):
  return ['  ' + line for line in lines]

def IsInlineComment(token):
  return token and token[0] == tokenize.COMMENT and token[-1].strip()[0] != '#'
