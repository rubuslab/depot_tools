# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import argparse
import collections
import json
import logging
import os
import re
import subprocess
import sys


SELF_PATH = os.path.abspath(os.path.dirname(__file__))
DEPOT_TOOLS = os.path.abspath(
    os.path.join(SELF_PATH, os.pardir, os.pardir, os.pardir, os.pardir))

_GIT_HASH_RE = re.compile('[0-9a-f]{40}', re.IGNORECASE)


# Status is the output JSON object.
Status = collections.namedtuple('Status', ('head',))


def _execute(args, cwd, env, capture_output, dry_run):
  logging.info('Executing command (cwd=%s): %s', cwd, ' '.join(args))
  if dry_run:
    return 'dry run'
  if capture_output:
    return subprocess.check_output(args, cwd=cwd, env=env)
  subprocess.check_call(args, cwd=cwd, env=env)
  return None


class Git(object):

  def __init__(self, git_path, checkout_path, env, dry_run):
    self._git = git_path
    self._checkout = checkout_path
    self._dry_run = dry_run
    self._env = env or os.environ.copy()

  @classmethod
  def from_args(cls, args):
    return cls(args.git_cmd_path, args.dir, None, args.debug_dry_run)

  def log_info(self):
    logging.info('Using Git tool: %s', self._git)

    version = _execute([self._git, 'version'], None, self._env, True, False)
    logging.info('Using Git version: %s', version.strip())

  def call(self, *args):
    cmd = [self._git] + list(args)
    return _execute(cmd, self._checkout, self._env, False, self._dry_run)

  def output(self, *args):
    cmd = [self._git] + list(args)
    return _execute(cmd, self._checkout, self._env, True, self._dry_run)

  @staticmethod
  def _cache_cmd(args):
    cmd = [sys.executable, os.path.join(DEPOT_TOOLS, 'git_cache.py')]
    cmd += args
    return cmd

  def cache(self, *args):
    return _execute(self._cache_cmd(args), self._checkout, self._env, False,
                    self._dry_run)

  def cache_output(self, *args):
    return _execute(self._cache_cmd(args), self._checkout, self._env, True,
                    self._dry_run)


def _resolve_ref(ref):
  """Returns (fetch_ref, checkout_ref)."""
  # There are five kinds of refs we can be handed:
  # 0) None. In this case, we default to properties['branch'].
  # 1) A 40-character SHA1 hash.
  # 2) A fully-qualifed arbitrary ref, e.g. 'refs/foo/bar/baz'.
  # 3) A fully qualified branch name, e.g. 'refs/heads/master'.
  #    Chop off 'refs/heads' and now it matches case (4).
  # 4) A branch name, e.g. 'master'.
  # Note that 'FETCH_HEAD' can be many things (and therefore not a valid
  # checkout target) if many refs are fetched, but we only explicitly fetch
  # one ref here, so this is safe.
  if not ref:                         # Case 0
    return 'master', 'FETCH_HEAD'
  elif _GIT_HASH_RE.match(ref):       # Case 1.
    return None, ref
  elif ref.startswith('refs/heads/'): # Case 3.
    return ref[len('refs/heads/'):],  'FETCH_HEAD'
  else:                               # Cases 2 and 4.
    return ref, 'FETCH_HEAD'


def _do_setup(git, args):
  logging.info('Initializing Git repository at: %s', args.dir)
  if not os.path.exists(args.dir):
    logging.info('Creating missing Git directory: %s', args.dir)
    os.makedirs(args.dir)

  if os.path.exists(os.path.join(args.dir, '.git')):
    # Remove any previously-defined remotes.
    try:
      git.call('config', '--remove-section', 'remote.%s' % args.remote_name)
    except subprocess.CalledProcessError:
      pass
  else:
    git.call('init')
  git.call('remote', 'add', args.remote_name, args.url)

  if args.git_cache_dir:
    logging.info('Setting up Git cache from: %s', args.git_cache_dir)
    git.cache('populate', '-c', args.git_cache_dir, args.url)
    mirror_dir = git.cache_output('exists', '--quiet', '--cache-dir',
                                  args.git_cache_dir, args.url)
    mirror_dir = mirror_dir.strip()
    git.call('remote', 'set-url', args.remote_name, mirror_dir)

  return Status(head=None)


def _do_checkout(git, args):
  # Perform fetch.
  fetch_ref, checkout_ref = _resolve_ref(args.ref)
  logging.info('Fetching ref [%s], and checking out ref [%s]',
                fetch_ref, checkout_ref)
  cmd = ['fetch', args.remote_name]
  if fetch_ref:
    cmd.append(fetch_ref)
  if args.recurse:
    cmd.append('--recurse-submodules')
  git.call(*cmd)
  git.call('checkout', '--force', checkout_ref)

  # Capture the revision that we got.
  revision = git.output('rev-parse', 'HEAD').strip()

  # Submodules / recurse.
  if args.recurse:
    git.call('submodule', 'sync')
    git.call('submodule', 'update', '--init', '--recursive', '--force')

  # Clean.
  if args.clean:
    logging.info('Performing post-checkout clean, keeping: %s', args.clean_keep)
    cmd = ['clean', '-f', '-d', '-x']
    for keep in args.clean_keep:
      cmd += ['-e', keep]
    git.call(*cmd)

  return Status(
      head=revision)


def _setup(args):
  git = Git.from_args(args)
  git.log_info()
  return _do_setup(git, args)


def _ensure_checkout(args):
  git = Git.from_args(args)
  git.log_info()
  _do_setup(git, args)
  return _do_checkout(git, args)


def main():
  parser = argparse.ArgumentParser()
  parser.add_argument('--output-json', type=argparse.FileType('w'),
      help='The path to write output JSON to.')
  parser.add_argument('--git-cmd-path', default='git',
      help='Path to the Git command to use (default is %(default)s).')
  parser.add_argument('--git-cache-dir',
      help='If true, use Git cache in this directory.')
  parser.add_argument('--debug-dry-run', action='store_true',
      help='Log commands, but refrain from executing them.')

  subparsers = parser.add_subparsers()

  subparser = subparsers.add_parser('setup')
  def add_setup_args(subparser):
    subparser.add_argument('--dir', required=True,
        help='The target Git directory.')
    subparser.add_argument('--url', required=True,
        help='The URL of the repository to check out.')
    subparser.add_argument('--remote-name', default='origin',
        help='The remote name (default is %(default)s).')
  add_setup_args(subparser)
  subparser.set_defaults(func=_setup)

  subparser = subparsers.add_parser('ensure_checkout')
  add_setup_args(subparser)
  subparser.add_argument('--ref',
      help='The Git ref to check out. If empty, check out "master".')
  subparser.add_argument('--recurse', action='store_true',
      help='Recursively checkout Git submodules.')
  subparser.add_argument('--clean', action='store_true',
      help='Perform a clean operation on the repository.')
  subparser.add_argument('--clean-keep', action='append', default=[],
      help='If cleaning, omit these Git-style paths.')
  subparser.set_defaults(func=_ensure_checkout)

  args = parser.parse_args()

  status = args.func(args)
  if args.output_json:
    with args.output_json:
      json.dump(status._asdict(), args.output_json)
  return 0


if __name__ == '__main__':
  logging.basicConfig(level=logging.INFO)
  sys.exit(main())
