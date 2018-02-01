from redbaron import RedBaron


def _Value(query, to_python=False):
  if to_python:
    return lambda node: node.to_python() == query
  return lambda node: node.value == query

def _IsVar(node):
  return 'atomtrailers' in node.generate_identifiers()

def _IsDict(node):
  return 'dict' in node.generate_identifiers()

def _Query(red_dict, query):
  return red_dict.find(
      "dictitem",
      key=_Value(query, to_python=True)).value


class DepsFile(object):
  def __init__(self):
    with open("DEPS") as f:
      self._red = RedBaron(f.read())

    self._deps_dict = self._red.find(
        "assignment",
        operator="",
        target=_Value("deps")).value

    self._vars_dict = self._red.find(
        "assignment",
        operator="",
        target=_Value("vars")).value

  def GetDependency(self, dep_name):
    return Dependency(_Query(self._deps_dict, dep_name),
                      self._vars_dict)

  def Write(self):
    with open("DEPS", "w") as f:
      f.write(self._red.dumps())


class Dependency(object):
  def __init__(self, red_dependency, vars_dict):
    self._condition = None
    if _IsDict(red_dependency):
      self._condition = _Query(red_dependency, 'condition')
      red_dependency = _Query(red_dependency, 'url')

    self._origin = _Query(vars_dict, self._VarArgument(red_dependency.first))
    self._path = red_dependency.second.first
    self._revision = red_dependency.second.second.second
    if _IsVar(self._revision):
      self._revision = _Query(vars_dict, self._VarArgument(self._revision))

  def _VarArgument(self, node):
    return node[1][0].value.to_python()

  @property
  def revision(self):
    return self._revision.to_python()

  @revision.setter
  def revision(self, revision):
    self._revision.value = repr(revision)


deps_file = DepsFile()
print deps_file.GetDependency("src/v8").revision
deps_file.GetDependency("src/v8").revision = 'deadbeef'
print deps_file.GetDependency("src/v8").revision
print deps_file.GetDependency("src/native_client").revision
print deps_file.GetDependency("src/third_party/auto/src").revision
print deps_file.GetDependency("src/third_party/libsrtp").revision
print deps_file.GetDependency("src/third_party/material_design_icons/src").revision
deps_file.GetDependency("src/third_party/material_design_icons/src").revision = 'new-rev'
print deps_file.GetDependency("src/third_party/material_design_icons/src").revision
deps_file.Write()
