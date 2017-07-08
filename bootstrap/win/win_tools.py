# Copyright 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import argparse
import collections
import contextlib
import fnmatch
import hashlib
import logging
import os
import platform
import shutil
import string
import subprocess
import sys
import tempfile


THIS_DIR = os.path.abspath(os.path.dirname(__file__))
ROOT_DIR = os.path.abspath(os.path.join(THIS_DIR, '..', '..'))

DEVNULL = open(os.devnull, 'w')

BAT_EXT = '.bat' if sys.platform.startswith('win') else ''

# Top-level stubs to generate that fall through to executables within the Git
# directory.
STUBS = {
  'git.bat': 'cmd\\git.exe',
  'gitk.bat': 'cmd\\gitk.exe',
  'ssh.bat': 'usr\\bin\\ssh.exe',
  'ssh-keygen.bat': 'usr\\bin\\ssh-keygen.exe',
}


# Accumulated template parameters for generated stubs.
class Template(collections.namedtuple('Template', (
    'PYTHON_RELDIR', 'PYTHON_RELDIR_UNIX',
    'GIT_BIN_DIR', 'GIT_PROGRAM',
    ))):

  @classmethod
  def empty(cls):
    return cls(**{k: None for k in cls._fields})

  def maybe_install(self, src_name, path):
    with open(os.path.join(THIS_DIR, src_name), 'r') as fd:
      t = string.Template(fd.read())
    new_content = t.safe_substitute(self._asdict())

    # If the path already exists and matches the template, refrain from writing
    # a new one.
    if os.path.exists(path):
      with open(path, 'r') as fd:
        if fd.read() == new_content:
          return False

    logging.debug('Updating template %r => %r', src_name, path)
    with open(path, 'w') as fd:
      fd.write(new_content)
    return True


def _in_use(path):
  """Checks if a Windows file is in use."""
  try:
    with open(path, 'r+'):
      return False
  except IOError:
    return True


def _check_call(argv, stdin_input=None, **kwargs):
  """Wrapper for subprocess.check_call that adds logging."""
  logging.info('running %r', argv)
  if stdin_input is not None:
    kwargs['stdin'] = subprocess.PIPE
  proc = subprocess.Popen(argv, **kwargs)
  proc.communicate(input=stdin_input)
  if proc.returncode:
    raise subprocess.CalledProcessError(proc.returncode, argv, None)


def _safe_rmtree(path):
  if not os.path.exists(path):
    return

  def _make_writable_and_remove(path):
    st = os.stat(path)
    new_mode = st.st_mode | 0200
    if st.st_mode == new_mode:
      return False
    try:
      os.chmod(path, new_mode)
      os.remove(path)
      return True
    except Exception:
      return False

  def _on_error(function, path, excinfo):
    if not _make_writable_and_remove(path):
      logging.warning('Failed to %s: %s (%s)', function, path, excinfo)

  shutil.rmtree(path, onerror=_on_error)


@contextlib.contextmanager
def _tempdir():
  tdir = None
  try:
    tdir = tempfile.mkdtemp()
    yield tdir
  finally:
    _safe_rmtree(tdir)


def get_os_bitness():
  """Returns bitness of operating system as int."""
  return 64 if platform.machine().endswith('64') else 32


def get_target_git_version(args):
  """Returns git version that should be installed."""
  if args.bleeding_edge:
    git_version_file = 'git_version_bleeding_edge.txt'
  else:
    git_version_file = 'git_version.txt'
  with open(os.path.join(THIS_DIR, git_version_file)) as f:
    return f.read().strip()


def clean_up_old_git_installations(git_directory, force):
  """Removes git installations other than |git_directory|."""
  for entry in fnmatch.filter(os.listdir(ROOT_DIR), 'git-*_bin'):
    full_entry = os.path.join(ROOT_DIR, entry)
    if force or full_entry != git_directory:
      logging.info('Cleaning up old git installation %r', entry)
      _safe_rmtree(full_entry)


def clean_up_old_python_installations(skip_dir):
  """Removes Python installations other than |skip_dir|.
  
  This includes an "in-use" check against the "python.exe" in a given directory
  to avoid removing Python executables that are currently ruinning. We need
  this because our Python bootstrap may be run after (and by) other software
  that is using the bootstrapped Python!
  """
  for entry in fnmatch.filter(os.listdir(ROOT_DIR), 'python27*_bin'):
    full_entry = os.path.join(ROOT_DIR, entry)
    if full_entry == skip_dir:
      continue

    logging.info('Cleaning up old Python installation %r', entry)
    for python_exe in (
        os.path.join(full_entry, 'bin', 'python.exe'), # CIPD Python bundles.
        os.path.join(full_entry, 'python.exe'), # Legacy ZIP distributions.
        ):
      if os.path.isfile(python_exe) and _in_use(python_exe):
        logging.info('Python executable %r is in-use; skipping', python_exe)
        break
    else:
      _safe_rmtree(full_entry)


def python_version_from_manifest(path, version_tag):
  """Extracts the Python version referenced by a CIPD Python manifest.

  This performs minimal manifest file parsing:
  - Ignores blank lines and comments.
  - Splits "package version".

  After identifying a line with a |version_tag| tag, it will return that tag's
  value.

  Raises:
    ValueError: if no version is identified.
  """
  token = version_tag + ':'
  with open(path, 'r') as fd:
    for line in fd:
      line = line.strip()
      if len(line) == 0 or line.startswith('#'):
        continue
      idx = line.find(token)
      if idx > 0:
        return line[idx+len(token):]
  raise ValueError('No manifest entry found containing %r.' % (token,))


def cipd_ensure(args, dest_directory, package=None, version=None,
                manifest_path=None):
  """Installs a CIPD manifest using "ensure".
  
  Either (|package|, |version|) or a |manifest_path| must be supplied.
  """
  if package and version:
    logging.info('Installing CIPD package %r @ %r', package, version)
    manifest_text = '%s %s\n' % (package, version)
    manifest_path = '-'
  elif manifest_path:
    logging.info('Installing CIPD manifest: %r', manifest_path)
    manifest_text = None
  else:
    raise ValueError('No package or manifest was supplied.')

  cipd_args = [
    args.cipd_client,
    'ensure',
    '-ensure-file', manifest_path,
    '-root', dest_directory,
  ]
  if args.cipd_cache_directory:
    cipd_args.extend(['-cache-dir', args.cipd_cache_directory])
  if args.verbose:
    cipd_args.append('-verbose')
  _check_call(cipd_args, stdin_input=manifest_text)


def need_to_install_git(args, git_directory, legacy):
  """Returns True if git needs to be installed."""
  if args.force:
    return True

  is_cipd_managed = os.path.exists(os.path.join(git_directory, '.cipd'))
  if legacy:
    if is_cipd_managed:
      # Converting from non-legacy to legacy, need reinstall.
      return True
    if not os.path.exists(os.path.join(
        git_directory, 'etc', 'profile.d', 'python.sh')):
      return True
  elif not is_cipd_managed:
    # Converting from legacy to CIPD, need reinstall.
    return True

  git_exe_path = os.path.join(git_directory, 'bin', 'git.exe')
  if not os.path.exists(git_exe_path):
    return True
  if subprocess.call(
      [git_exe_path, '--version'],
      stdout=DEVNULL, stderr=DEVNULL) != 0:
    return True

  gen_stubs = STUBS.keys()
  gen_stubs.append('git-bash')
  for stub in gen_stubs:
    full_path = os.path.join(ROOT_DIR, stub)
    if not os.path.exists(full_path):
      return True
    with open(full_path) as f:
      if os.path.relpath(git_directory, ROOT_DIR) not in f.read():
        return True

  return False


def install_git_legacy(args, git_version, git_directory, cipd_platform):
  _safe_rmtree(git_directory)
  with _tempdir() as temp_dir:
    cipd_ensure(args, temp_dir,
        package='infra/depot_tools/git_installer/%s' % cipd_platform,
        version='v' + git_version.replace('.', '_'))

    # 7-zip has weird expectations for command-line syntax. Pass it as a string
    # to avoid subprocess module quoting breaking it. Also double-escape
    # backslashes in paths.
    _check_call(' '.join([
      os.path.join(temp_dir, 'git-installer.exe'),
      '-y',
      '-InstallPath="%s"' % git_directory.replace('\\', '\\\\'),
      '-Directory="%s"' % git_directory.replace('\\', '\\\\'),
    ]))


def install_git(args, template, git_version, git_directory, legacy):
  """Installs |git_version| into |git_directory|."""
  # TODO: Remove legacy version once everyone is on bundled Git.
  cipd_platform = 'windows-%s' % ('amd64' if args.bits == 64 else '386')
  if legacy:
    install_git_legacy(args, git_version, git_directory, cipd_platform)
  else:
    # When migrating from legacy, we want to nuke this directory. In other
    # cases, CIPD will handle the cleanup.
    if not os.path.isdir(os.path.join(git_directory, '.cipd')):
      logging.info('Deleting legacy Git directory: %s', git_directory)
      _safe_rmtree(git_directory)

    cipd_ensure(args, git_directory,
        package='infra/git/%s' % (cipd_platform,),
        version=git_version)

  # Create Git templates and configure its base layout.
  for stub_name, relpath in STUBS.iteritems():
    stub_template = template._replace(GIT_PROGRAM=relpath)
    stub_template.maybe_install(
        'git.template.bat', 
        os.path.join(ROOT_DIR, stub_name))

  if legacy:
    # The non-legacy Git bundle includes "python.sh".
    #
    # TODO: Delete "profile.d.python.sh" after legacy mode is removed.
    shutil.copyfile(
        os.path.join(THIS_DIR, 'profile.d.python.sh'),
        os.path.join(git_directory, 'etc', 'profile.d', 'python.sh'))

  git_bat_path = os.path.join(ROOT_DIR, 'git.bat')
  _check_call([git_bat_path, 'config', '--system', 'core.autocrlf', 'false'])
  _check_call([git_bat_path, 'config', '--system', 'core.filemode', 'false'])
  _check_call([git_bat_path, 'config', '--system', 'core.preloadindex', 'true'])
  _check_call([git_bat_path, 'config', '--system', 'core.fscache', 'true'])


def ensure_python(args, template):
  if not args.python_manifest:
    logging.info('(legacy) No Python manifest; refraining from installation.')
    template.maybe_install(
        'python276.new.bat',
        os.path.join(ROOT_DIR, 'python.bat'))
    return template

  # Load our Python manifest, and parse it to determine our Python installation
  # directory.
  #
  # The installation directory must correspond to the directory pattern used in
  # clean_up_old_python_installations.
  name = python_version_from_manifest(args.python_manifest, 'version')
  name = name.replace('.', '_')
  install_reldir = 'python27-%s_bin' % (name,)
  install_dir = os.path.join(ROOT_DIR, install_reldir)

  # Ensure our Python installation.
  cipd_ensure(args, install_dir, manifest_path=args.python_manifest)

  template = template._replace(
      PYTHON_RELDIR=install_reldir,
      PYTHON_RELDIR_UNIX=install_reldir.replace('\\', '/'))

  # Install our "python.bat" shim.
  #
  # TODO: Move this to generic shim installation once legacy support is removed
  # and this code path is the only one.
  template.maybe_install(
      'python_reldir.new.txt',
      os.path.join(ROOT_DIR, 'python_reldir.txt'))
  template.maybe_install(
      'python27.new.bat',
      os.path.join(ROOT_DIR, 'python.bat'))

  # Clean up any old Python installations.
  clean_up_old_python_installations(install_dir)

  return template


def ensure_git(args, template):
  git_version = get_target_git_version(args)

  git_directory_tag = git_version.split(':')
  git_directory = os.path.join(
      ROOT_DIR, 'git-%s-%s_bin' % (git_directory_tag[-1], args.bits))
  git_docs_dir = os.path.join(
      git_directory, 'mingw%s' % args.bits, 'share', 'doc', 'git-doc')

  clean_up_old_git_installations(git_directory, args.force)

  template = template._replace(
      GIT_BIN_DIR=os.path.relpath(git_directory, ROOT_DIR))

  # Modern Git versions use CIPD tags beginning with "version:". If the tag
  # does not begin with that, use the legacy installer.
  legacy = not git_version.startswith('version:')
  if need_to_install_git(args, git_directory, legacy):
    install_git(args, template, git_version, git_directory, legacy)

  # Update depot_tools files for "git help <command>"
  docsrc = os.path.join(ROOT_DIR, 'man', 'html')
  for name in os.listdir(docsrc):
    shutil.copy2(os.path.join(docsrc, name), os.path.join(git_docs_dir, name))

  return template


def main(argv):
  parser = argparse.ArgumentParser()
  parser.add_argument('--force', action='store_true',
                      help='Always re-install everything.')
  parser.add_argument('--python-manifest',
                      help='The Python manifest to use. If empty, disable '
                           'Python installation (legacy).')
  parser.add_argument('--bleeding-edge', action='store_true',
                      help='Force bleeding edge Git.')
  parser.add_argument('--bits', type=int, choices=(32,64),
                      help='Bitness of the client to install. Default on this'
                      ' system: %(default)s', default=get_os_bitness())
  parser.add_argument('--cipd-client',
                      help='Path to CIPD client binary. default: %(default)s',
                      default=os.path.join(ROOT_DIR, 'cipd'+BAT_EXT))
  parser.add_argument('--cipd-cache-directory',
                      help='Path to CIPD cache directory.')
  parser.add_argument('--verbose', action='store_true')
  args = parser.parse_args(argv)

  logging.basicConfig(level=logging.DEBUG if args.verbose else logging.WARN)

  template = Template.empty()
  template = ensure_python(args, template)
  template = ensure_git(args, template)

  # Re-evaluate and regenerate our root templated files.
  for src_name, dst_name in (
      ('git-bash.template.sh', 'git-bash'),
      ('pylint.new.bat', 'pylint.bat'),
      ):
    template.maybe_install(src_name, os.path.join(ROOT_DIR, dst_name))

  return 0


if __name__ == '__main__':
  sys.exit(main(sys.argv[1:]))
