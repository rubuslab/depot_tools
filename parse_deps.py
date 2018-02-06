import ast
import cStringIO
import pprint
import tokenize


def _ToDict(ast_dict):
  return {key.s: value for key, value in zip(ast_dict.keys, ast_dict.values)}


class DepsFile(object):
  def __init__(self, deps_file):
    self._deps_file = deps_file

    with open(self._deps_file) as f:
      contents = f.read()

    # Create a dictionary from token positions (line numbers and column offsets)
    # to the token information.
    self._tokens = {
        token[2]: list(token)
        for token in tokenize.generate_tokens(
            cStringIO.StringIO(contents).readline)
    }

    self._ast = ast.parse(contents).body
    self._deps_dict = _ToDict(self._FindDeclaration('deps'))
    self._vars_dict = _ToDict(self._FindDeclaration('vars'))

  def _FindDeclaration(self, name):
    # Finds a node of the form 'name = <value>' and returns <value> or None if
    # it doesn't exist
    for node in self._ast:
      if (isinstance(node, ast.Assign)
          and len(node.targets) == 1
          and isinstance(node.targets[0], ast.Name)
          and node.targets[0].id == name):
        return node.value
    return None

  def GetDependency(self, dep_name):
    return Dependency(self._deps_dict[dep_name], self._vars_dict, self._tokens)

  def Write(self, out_file=None):
    out_file = out_file or self._deps_file
    # Sort tokens according to their (line number, column offset).
    contents = sorted(self._tokens.values(), key=lambda token: token[2])
    with open(out_file, "w") as f:
      f.write(tokenize.untokenize(contents))


class Dependency(object):
  def __init__(self, ast_dep, vars_dict, tokens):
    # This is of the form.
    # 'dep': {'url': <revision_info>,
    #         'condition': <condition>}
    # Get the <revision_info> out.
    if isinstance(ast_dep, ast.Dict):
      ast_dep = _ToDict(ast_dep)['url']

    self._revision = ast_dep.right
    # The revision is of the form Var('dep_name'). Get the revision from the
    # vars dictionary.
    if isinstance(self._revision, ast.Call):
      revision_name = self._revision.args[0].s
      self._revision = vars_dict[revision_name]

    self._tokens = tokens

  @property
  def revision(self):
    return self._revision.s

  @revision.setter
  def revision(self, revision):
    position = (self._revision.lineno, self._revision.col_offset)
    self._revision.s = revision
    self._tokens[position][1] = repr(revision)


deps_file = DepsFile("DEPS")
print deps_file.GetDependency("src/v8").revision
deps_file.GetDependency("src/v8").revision = 'deadbeef'
print deps_file.GetDependency("src/v8").revision
print deps_file.GetDependency("src/native_client").revision
print deps_file.GetDependency("src/third_party/auto/src").revision
print deps_file.GetDependency("src/third_party/libsrtp").revision
print deps_file.GetDependency("src/third_party/material_design_icons/src").revision
deps_file.GetDependency("src/third_party/material_design_icons/src").revision = 'new-rev'
print deps_file.GetDependency("src/third_party/material_design_icons/src").revision

deps_file.Write("DEPS2")
