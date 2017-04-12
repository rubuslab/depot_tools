#!/usr/bin/env python
# Copyright (c) 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Applies a Gerrit change stored in a Git ref.
"""

import logging
import optparse
import os
import subprocess2
import sys
import uuid

import apply_issue
import fix_encoding
import gclient_utils
import scm


RETURN_CODE_OK               = 0
RETURN_CODE_OTHER_FAILURE    = 1  # any other failure, likely patch apply one.
RETURN_CODE_ARGPARSE_FAILURE = 2  # default in python.
RETURN_CODE_INFRA_FAILURE    = 3  # considered as infra failure.


def git(*args, **kwargs):
  """Yet another git subprocess2 wrapper."""
  assert 'cwd' in kwargs
  git_executable = 'git.bat' if sys.platform.startswith('win') else 'git'
  return gclient_utils.CheckCallAndFilter(
      (git_executable,) + args,
      print_stdout=True,
      **kwargs)


def apply_ref(cwd, remote, ref, rebase, base_rev, reset_soft):
  """Applies a patch from a gerrit ref.

  Returns one of:
    RETURN_CODE_OK
    RETURN_CODE_INFRA_FAILURE
    RETURN_CODE_OTHER_FAILURE
  """
  try:
    return _apply_ref_inner(cwd, remote, ref, rebase, base_rev, reset_soft)
  except subprocess2.CalledProcessError:
    return RETURN_CODE_INFRA_FAILURE


def _apply_ref_inner(cwd, remote, ref, rebase, base_rev, reset_soft):
  # TODO(tAndrii): if this fails it might actually be due to ref not existing.
  # which will be incorrectly reported as RETURN_CODE_INFRA_FAILURE instead
  # of RETURN_CODE_OTHER_FAILURE.
  git('retry', 'fetch', remote, ref, cwd=cwd)

  git('checkout', 'FETCH_HEAD', cwd=cwd)

  if rebase:
    print('===Rebasing %s on top of %s===' % (ref, base_rev))
    # git rebase requires a branch to operate on.
    temp_branch_name='tmp/' + uuid.uuid4().hex
    final_rev = base_rev
    try:
      ok = False
      git('checkout', '-b', temp_branch_name, cwd=cwd)

      try:
        git('rebase', base_rev, cwd=cwd)
      except subprocess2.CalledProcessError:
        git('rebase', '--abort', cwd=cwd)
        return RETURN_CODE_OTHER_FAILURE

      final_rev = git('rev-parse', 'HEAD', cwd=cwd).strip()
    finally:
      git('checkout', final_rev, cwd=cwd)
      git('branch', '-D', temp_branch_name, cwd=cwd)

  if reset_soft:
    print('===Soft resetting against %s===' % base_rev)
    git('reset', '--soft', base_rev, cwd=cwd)
  return RETURN_CODE_OK


def _get_arg_parser():
  parser = optparse.OptionParser(description=sys.modules[__name__].__doc__)
  parser.add_option(
      '-v', '--verbose', action='count', default=0,
      help='Prints debugging infos')
  parser.add_option(
      '--ref', type='str',
      help='git ref containing the patch, typically refs/changes/XX/YYYYXX/ZZ')
  parser.add_option(
      '--remote', type='str', default='origin',
      help='url or name of git remote')
  parser.add_option(
      '--git_dir', default=os.getcwd(),
      help='path to git repository in which to apply the ref')
  parser.add_option(
      '--no_rebase', default=False,
      help='do not rebase, just check out the ref')
  parser.add_option(
      '--base', default=None,
      help='base revision on top of which to rebase the patch. '
           'By default, uses HEAD at the time of invocation.')
  parser.add_option(
      '--reset_soft', default=False, action='store_true',
      help='calls git reset --soft against base revision after apply patch')
  return parser


def main():
  sys.stdout = apply_issue.Unbuffered(sys.stdout)
  parser = _get_arg_parser()
  options, args = parser.parse_args()

  if args:
    parser.error('Extra argument(s) "%s" not understood' % ' '.join(args))
  del args

  if not options.ref:
    parser.error('Requires --ref')

  if options.reset_soft and options.no_rebase:
    print('WARNING: --reset_soft should NOT be used with --no_rebase')
  # TODO(tandrii): prohibit using reset without rebase, as it makes no sense.
  # And then prohibit simultaneous use of --no_rebase and --base as well.
  # These possibilities are kept alive for now for migrating bot_update recipe
  # to this tool.
  # if options.no_rebase and options.base:
  #  parser.error('Options --no_rebase and --base are mutually exclusive')

  logging.basicConfig(
      format='%(levelname)5s %(module)11s(%(lineno)4d): %(message)s',
      level=[logging.WARNING, logging.INFO, logging.DEBUG][
          min(2, options.verbose)])

  git_dir = os.path.abspath(options.git_dir)
  if 'git' != scm.determine_scm(git_dir):
    parser.error('%s is not a git repository' % opts.git_dir)

  try:
    base_rev = git('rev-parse', options.base or 'HEAD', cwd=git_dir).strip()
  except subprocess2.CalledProcessError:
    parser.error('invalid base: %s' % options.base)

  # Use git_dir which is top of git repo in case os.getcwd() is in deleted
  # folder after patch is applied.
  relative_git_root = git('rev-parse', '--show-cdup', cwd=git_dir).strip()
  git_dir = os.path.join(git_dir, relative_git_root)
  return apply_ref(git_dir, options.remote, options.ref,
                   not options.no_rebase, base_rev, options.reset_soft)


if __name__ == "__main__":
  fix_encoding.fix_encoding()
  try:
    sys.exit(main())
  except KeyboardInterrupt:
    sys.stderr.write('interrupted\n')
    sys.exit(RETURN_CODE_OTHER_FAILURE)
