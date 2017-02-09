# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from collections import namedtuple

from recipe_engine import recipe_api
from recipe_engine.config_types import Path

def ckType(name, var, expect):
  if not isinstance(var, expect):
    raise TypeError("%s is not %s: %r (%s)" % (
      name, type(expect).__name__, var, type(var).__name__))

def ckListType(name, var, expect_inner):
  ckType(name, var, list)
  for i, itm in enumerate(var):
    ckType('%s[%d]' % (name, i), itm, expect_inner)

def ckDictType(name, var, expect_key, expect_value):
  ckType(name, var, dict)
  for key, value in var.iteritems():
    ckType('%s: key' % name, key, expect_key)
    ckType('%s[%s]' % (name, key), value, expect_value)

class PackageDefinition(object):
  DIR = namedtuple("DIR", ['path', 'exclusions'])

  def __init__(self, package_name, package_root, install_mode):
    """Build a new PackageDefinition.

    Args:
      package_name (str) - the name of the CIPD package
      package_root (Path) - the path on the current filesystem that all files
        will be relative to. e.g. if your root is /.../foo, and you add the
        file /.../foo/bar/baz.json, the final cipd package will contain
        "bar/baz.json".
      install_mode ("copy"|"symlink") - the method that cipd clients will use
        to unpack this package locally.
    """
    ckType('package_name', package_name, str)
    ckType('package_root', package_root, Path)
    ckType('install_mode', install_mode, str)
    if install_mode not in ('copy', 'symlink'):
      raise ValueError('invalid value for install_mode: %r' % install_mode)
    self.package_name = package_name
    self.package_root = package_root
    self.install_mode = install_mode

    self.dirs = []  # list(DIR)
    self.files = []  # list(Path)
    self.version_file = None  # str?

  def _checkIn(self, path):
    if not self.package_root.is_parent_of(path):
      raise ValueError("path %r is not a child of the package root %r" %
                       (path, self.package_root))

  def add_dir(self, dir_path, exclusions=None):
    """Recursively add a directory to the package.

    Args:
      dir_path (Path) - A path on the current filesystem under the
        package_root to a directory which should be recursively included.
      exclusions (list(str)) - A list of globs to exclude when scanning the
        given directory.
    """
    ckType('dir_path', dir_path, Path)
    self._checkIn(dir_path)
    exclusions = exclusions or []
    ckListType('exclusions', exclusions, str)
    self.dirs.append(self.DIR(dir_path, exclusions))

  def add_file(self, file_path):
    """Add a single file to the package.

    Args:
      file_path (Path) - A path on the current filesystem to the file you
        wish to include.
    """
    ckType('file_path', file_path, Path)
    self._checkIn(file_path)
    self.files.append(file_path)

  def add_version_file(self, ver_file_rel):
    """Instruct the cipd client to place a version file in this location when
    unpacking the package.

    Version files are JSON which look like: {
      "package_name": "infra/tools/cipd/android-amd64",
      "instance_id": "433bfdf86c0bb82d1eee2d1a0473d3709c25d2c4"
    }

    The convention is to pick a location like ".versions/<name>.cipd_version"
    so that a given cipd installation root might have a .versions folder full
    of these files, one per package. This file allows executables contained
    in the package to look for and report this file, allowing them to display
    version information about themselves. <name> could be the name of the
    binary tool, like 'cipd' in the example above.

    A version file may be specifed exactly once per package.

    Args:
      ver_file_rel (str) - A path string relative to the installation root.
        Should be specified in posix style (forward/slashes).
    """
    ckType('ver_file_rel', ver_file_rel, str)
    if self.version_file is not None:
      raise ValueError("add_version_file() may only be used once.")
    self.version_file = ver_file_rel

  def to_jsonish(self):
    """Returns a JSON representation of this PackageDefinition."""
    return {
      "package": self.package_name,
      "root": str(self.package_root),
      "install_mode": self.install_mode,
      "data": [
        {"file": str(f)}
        for f in self.files
      ]+[
        {"dir": str(d.path), "exclude": d.exclusions}
        for d in self.dirs
      ]+([{"version_file": self.version_file}] if self.version_file else [])
    }


class CIPDApi(recipe_api.RecipeApi):
  """CIPDApi provides support for CIPD."""
  PackageDefinition = PackageDefinition

  def __init__(self, *args, **kwargs):
    super(CIPDApi, self).__init__(*args, **kwargs)
    self._cipd_executable = None
    self._cipd_version = None
    self._cipd_credentials = None

  def set_service_account_credentials(self, path):
    self._cipd_credentials = path

  @property
  def default_bot_service_account_credentials(self):
    # Path to a service account credentials to use to talk to CIPD backend.
    # Deployed by Puppet.
    if self.m.platform.is_win:
      return 'C:\\creds\\service_accounts\\service-account-cipd-builder.json'
    else:
      return '/creds/service_accounts/service-account-cipd-builder.json'

  def platform_suffix(self):
    """Use to get full package name that is platform indepdent.

    Example:
      >>> 'my/package/%s' % api.cipd.platform_suffix()
      'my/package/linux-amd64'
    """
    return '%s-%s' % (
        self.m.platform.name.replace('win', 'windows'),
        {
            32: '386',
            64: 'amd64',
        }[self.m.platform.bits],
    )

  def install_client(self, step_name='install cipd', version=None):
    """Ensures the client is installed.

    If you specify version as a hash, make sure its correct platform.
    """
    # TODO(seanmccullough): clean up older CIPD installations.
    step = self.m.python(
        name=step_name,
        script=self.resource('bootstrap.py'),
        args=[
          '--platform', self.platform_suffix(),
          '--dest-directory', self.m.path['start_dir'].join('cipd'),
          '--json-output', self.m.json.output(),
        ] +
        (['--version', version] if version else []),
        step_test_data=lambda: self.test_api.example_install_client(version)
    )
    self._cipd_executable = step.json.output['executable']

    step.presentation.step_text = (
        'cipd instance_id: %s' % step.json.output['instance_id'])
    return step

  @property
  def executable(self):
    if not self._cipd_executable:
      raise ValueError(
        "Your recipe must call install_client() before using"
        " other methods on the depot_tools/cipd module.")
    return self._cipd_executable

  def build(self, input_dir, output_package, package_name, install_mode=None):
    assert not install_mode or install_mode in ['copy', 'symlink']
    return self.m.step(
        'build %s' % self.m.path.basename(package_name),
        [
          self.executable,
          'pkg-build',
          '-in', input_dir,
          '-name', package_name,
          '-out', output_package,
          '-json-output', self.m.json.output(),
        ] + (
          ['-install-mode', install_mode] if install_mode else []
        ),
        step_test_data=lambda: self.test_api.example_build(package_name)
    )

  def register(self, package_name, package_path, refs=None, tags=None):
    cmd = [
      self.executable,
      'pkg-register', package_path,
      '-json-output', self.m.json.output(),
    ]
    if self._cipd_credentials:
      cmd.extend(['-service-account-json', self._cipd_credentials])
    if refs:
      for ref in refs:
        cmd.extend(['-ref', ref])
    if tags:
      for tag, value in sorted(tags.items()):
        cmd.extend(['-tag', '%s:%s' % (tag, value)])
    return self.m.step(
        'register %s' % package_name,
        cmd,
        step_test_data=lambda: self.test_api.example_register(package_name)
    )

  def _create(self, pkg_name, pkg_def_file_or_placeholder,
              refs=None, tags=None):
    refs = refs or []
    tags = tags or {}
    ckListType('refs', refs, str)
    ckDictType('tags', tags, str, str)
    cmd = [
      self.executable,
      'create',
      '-pkg-def', pkg_def_file_or_placeholder,
      '-json-output', self.m.json.output(),
    ]
    if self._cipd_credentials:
      cmd.extend(['-service-account-json', self._cipd_credentials])
    for ref in refs:
      cmd.extend(['-ref', ref])
    for tag, value in sorted(tags.items()):
      cmd.extend(['-tag', '%s:%s' % (tag, value)])
    result = self.m.step(
      'create %s' % pkg_name, cmd,
      step_test_data=lambda: self.test_api.m.json.output({
        "result": self.test_api.make_pin(pkg_name),
      }))
    ret_data = result.json.output['result']
    result.presentation.step_text = "</br>pkg: %(package)s" % ret_data
    result.presentation.step_text += "</br>id: %(instance_id)s" % ret_data
    return ret_data

  def create_from_yaml(self, pkg_def, refs=None, tags=None):
    """Builds and uploads a package based on on-disk YAML package definition
    file.

    This builds and uploads the package in one step.

    Args:
      pkg_def (Path) - The path to the yaml file.
      refs (list(str)) - A list of ref names to set for the package instance.
      tags (dict(str, str)) - A map of tag name -> value to set for the package
                              instance.

    Returns the JSON 'result' section, e.g.: {
      "package": "infra/tools/cipd/android-amd64",
      "instance_id": "433bfdf86c0bb82d1eee2d1a0473d3709c25d2c4"
    }
    """
    ckType('pkg_def', pkg_def, Path)
    return self._create(self.m.path.basename(pkg_def), pkg_def, refs, tags)

  def create_from_pkg(self, pkg_def, refs=None, tags=None):
    """Builds and uploads a package based on on-disk YAML package definition
    file.

    This builds and uploads the package in one step.

    Args:
      pkg_def (PackageDefinition) - The PackageDefinition object to create.
      refs (list(str)) - A list of ref names to set for the package instance.
      tags (dict(str, str)) - A map of tag name -> value to set for the package
                              instance.

    Returns the JSON 'result' section, e.g.: {
      "package": "infra/tools/cipd/android-amd64",
      "instance_id": "433bfdf86c0bb82d1eee2d1a0473d3709c25d2c4"
    }
    """
    ckType('pkg_def', pkg_def, PackageDefinition)
    return self._create(
      pkg_def.package_name, self.m.json.input(pkg_def.to_jsonish()), refs, tags)


  def ensure(self, root, packages):
    """Ensures that packages are installed in a given root dir.

    packages must be a mapping from package name to its version, where
      * name must be for right platform (see also ``platform_suffix``),
      * version could be either instance_id, or ref, or unique tag.

    If installing a package requires credentials, call
    ``set_service_account_credentials`` before calling this function.
    """
    package_list = ['%s %s' % (name, version)
                    for name, version in sorted(packages.items())]
    ensure_file = self.m.raw_io.input('\n'.join(package_list))
    cmd = [
      self.executable,
      'ensure',
      '-root', root,
      '-ensure-file', ensure_file,
      '-json-output', self.m.json.output(),
    ]
    if self._cipd_credentials:
      cmd.extend(['-service-account-json', self._cipd_credentials])
    self.m.step(
        'ensure_installed', cmd,
        step_test_data=lambda: self.test_api.example_ensure(packages)
    )

  def set_tag(self, package_name, version, tags):
    cmd = [
      self.executable,
      'set-tag', package_name,
      '-version', version,
      '-json-output', self.m.json.output(),
    ]
    if self._cipd_credentials:
      cmd.extend(['-service-account-json', self._cipd_credentials])
    for tag, value in sorted(tags.items()):
      cmd.extend(['-tag', '%s:%s' % (tag, value)])

    return self.m.step(
      'cipd set-tag %s' % package_name,
      cmd,
      step_test_data=lambda: self.test_api.example_set_tag(
          package_name, version
      )
    )

  def set_ref(self, package_name, version, refs):
    cmd = [
      self.executable,
      'set-ref', package_name,
      '-version', version,
      '-json-output', self.m.json.output(),
    ]
    if self._cipd_credentials:
      cmd.extend(['-service-account-json', self._cipd_credentials])
    for r in refs:
      cmd.extend(['-ref', r])

    return self.m.step(
      'cipd set-ref %s' % package_name,
      cmd,
      step_test_data=lambda: self.test_api.example_set_ref(
          package_name, version
      )
    )

  def search(self, package_name, tag):
    assert ':' in tag, 'tag must be in a form "k:v"'

    cmd = [
      self.executable,
      'search', package_name,
      '-tag', tag,
      '-json-output', self.m.json.output(),
    ]
    if self._cipd_credentials:
      cmd.extend(['-service-account-json', self._cipd_credentials])

    return self.m.step(
      'cipd search %s %s' % (package_name, tag),
      cmd,
      step_test_data=lambda: self.test_api.example_search(package_name)
    )

  def describe(self, package_name, version,
               test_data_refs=None, test_data_tags=None):
    cmd = [
      self.executable,
      'describe', package_name,
      '-version', version,
      '-json-output', self.m.json.output(),
    ]
    if self._cipd_credentials:
      cmd.extend(['-service-account-json', self._cipd_credentials])

    return self.m.step(
      'cipd describe %s' % package_name,
      cmd,
      step_test_data=lambda: self.test_api.example_describe(
          package_name, version,
          test_data_refs=test_data_refs,
          test_data_tags=test_data_tags
      )
    )
