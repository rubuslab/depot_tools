#!/usr/bin/env python
# Copyright (c) 2013 The Chromium Authors. All rights reserved.
# Copyright (C) Microsoft Corporation. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Components needed to run formatting commands on a changset"""

from __future__ import print_function

import clang_format
import dart_format
import git_common
import logging
import os
import re
import subprocess2
import sys


class MoveToDir(object):

  def __init__(self, directory):
    self.directory = directory
    self.olddir = None

  def __enter__(self):
    if self.directory:
      self.olddir = os.getcwd()
      os.chdir(self.directory)

  def __exit__(self, kind, value, traceback):
    if self.olddir:
      os.chdir(self.olddir)

def _RunCommand(args, error_ok=False, error_message=None, shell=False,
                **kwargs):
  try:
    return subprocess2.check_output(args, shell=shell, **kwargs)
  except subprocess2.CalledProcessError as e:
    logging.debug('Failed running %s', args)
    if not error_ok:
      raise Exception('Command "%s" failed.\n%s' %
                      (' '.join(args), error_message or e.stdout or ''))
    return e.stdout


def _RunGit(cmd, error_ok=False, **kwargs):
  """Returns stdout."""
  cmd = tuple(cmd)
  try:
    return git_common.run(*cmd, **kwargs)
  except subprocess2.CalledProcessError as e:
    logging.debug('Failed running %s', cmd)
    if not error_ok:
      raise Exception('Command "%s" failed.\n' % (' '.join(cmd)))
    return e.stdout


def _GetRelativeRoot():
  return _RunGit(['rev-parse', '--show-cdup']).strip()


def _BuildGitDiffCmds(diff_type, upstream_commit, args, allow_prefix=False):
  """Generates a diff command."""
  # Generate diff for the current branch's changes.
  diff_cmd_base = ['-c', 'core.quotePath=false', 'diff', '--no-ext-diff']

  if allow_prefix:
    # explicitly setting --src-prefix and --dst-prefix is necessary in the
    # case that diff.noprefix is set in the user's git config.
    diff_cmd_base += ['--src-prefix=a/', '--dst-prefix=b/']
  else:
    diff_cmd_base += ['--no-prefix']

  diff_cmd_base += [diff_type, upstream_commit, '--']

  # If we have too many arguments, we may need to split them up into multiple
  # commands
  base_length = len(' '.join(diff_cmd_base))
  diff_cmds = []

  if args:
    args_active = args[:]
    while len(args_active) > 0:
      cur_cmd = diff_cmd_base[:]
      cur_cmd_len = base_length
      while cur_cmd_len < 6000 and len(args_active) > 0:
        arg = args_active.pop()
        if os.path.isdir(arg) or os.path.isfile(arg):
          cur_cmd_len += len(' ' + arg)
          cur_cmd.append(arg)
        else:
          raise Exception('Argument "%s" is not a file or a directory' % arg)
      diff_cmds.append(cur_cmd)
  else:
    diff_cmds.append(diff_cmd_base)

  return diff_cmds


def _ClangFormat(clang_diff_files,
                 upstream_commit,
                 output,
                 top_dir=None,
                 full=False,
                 dry_run=False,
                 diff=False):
  # Locate the clang-format binary in the checkout
  try:
    clang_format_tool = clang_format.FindClangFormatToolInChromiumTree()
  except clang_format.NotFoundError:
    raise

  if full:
    cmd = [clang_format_tool]
    if not dry_run and not diff:
      cmd.append('-i')
    stdout = _RunCommand(cmd + clang_diff_files, cwd=top_dir)
    if diff:
      output.write(stdout)
  else:
    env = os.environ.copy()
    env['PATH'] = str(os.path.dirname(clang_format_tool))
    try:
      script = clang_format.FindClangFormatScriptInChromiumTree(
          'clang-format-diff.py')
    except clang_format.NotFoundError:
      raise

    cmd = [sys.executable, script, '-p0']
    if not dry_run and not diff:
      cmd.append('-i')

    diff_cmds = _BuildGitDiffCmds('-U0', upstream_commit, clang_diff_files)
    diff_output = ''
    for diff_cmd in diff_cmds:
      diff_output += _RunGit(diff_cmd)

    stdout = _RunCommand(cmd, stdin=diff_output, cwd=top_dir, env=env)
    if diff:
      output.write(stdout)
    if dry_run and len(stdout) > 0:
      return 2
  return 0


def _ComputeDiffLineRanges(files, upstream_commit):
  """Gets the changed line ranges for each file since upstream_commit.

  Parses a git diff on provided files and returns a dict that maps a file name
  to an ordered list of range tuples in the form (start_line, count).
  Ranges are in the same format as a git diff.
  """
  # If files is empty then diff_output will be a full diff.
  if len(files) == 0:
    return {}

  # Take the git diff and find the line ranges where there are changes.
  diff_cmds = _BuildGitDiffCmds(
      '-U0', upstream_commit, files, allow_prefix=True)
  line_diffs = {}
  for diff_cmd in diff_cmds:
    diff_output = _RunGit(diff_cmd)

    pattern = r'(?:^diff --git a/(?:.*) b/(.*))|(?:^@@.*\+(.*) @@)'
    # 2 capture groups
    # 0 == fname of diff file
    # 1 == 'diff_start,diff_count' or 'diff_start'
    # will match each of
    # diff --git a/foo.foo b/foo.py
    # @@ -12,2 +14,3 @@
    # @@ -12,2 +17 @@
    # running re.findall on the above string with pattern will give
    # [('foo.py', ''), ('', '14,3'), ('', '17')]

    curr_file = None
    for match in re.findall(pattern, diff_output, flags=re.MULTILINE):
      if match[0] != '':
        # Will match the second filename in diff --git a/a.py b/b.py.
        curr_file = os.path.normpath(match[0])
        line_diffs[curr_file] = []
      else:
        # Matches +14,3
        if ',' in match[1]:
          diff_start, diff_count = match[1].split(',')
        else:
          # Single line changes are of the form +12 instead of +12,1.
          diff_start = match[1]
          diff_count = 1

        diff_start = int(diff_start)
        diff_count = int(diff_count)

        # If diff_count == 0 this is a removal we can ignore.
        line_diffs[curr_file].append((diff_start, diff_count))

  return line_diffs


def _PythonFormat(python_diff_files,
                  upstream_commit,
                  output,
                  top_dir=None,
                  python_flag=None,
                  full=False,
                  diff=False,
                  dry_run=False):
  # File name for yapf style config files.
  YAPF_CONFIG_FILENAME = '.style.yapf'

  # Recursive method to find the yapf config file that applies to
  # a particular path
  def _FindYapfConfigFile(fpath, yapf_config_cache, top_dir=None):
    """Checks if a yapf file is in any parent directory of fpath until top_dir.

    Recursively checks parent directories to find yapf file and if no yapf file
    is found returns None. Uses yapf_config_cache as a cache for
    previously found configs.
    """
    fpath = os.path.abspath(fpath)
    # Return result if we've already computed it.
    if fpath in yapf_config_cache:
      return yapf_config_cache[fpath]

    parent_dir = os.path.dirname(fpath)
    if os.path.isfile(fpath):
      ret = _FindYapfConfigFile(parent_dir, yapf_config_cache, top_dir)
    else:
      # Otherwise fpath is a directory
      yapf_file = os.path.join(fpath, YAPF_CONFIG_FILENAME)
      if os.path.isfile(yapf_file):
        ret = yapf_file
      elif fpath == top_dir or parent_dir == fpath:
        # If we're at the top level directory, or if we're at root
        # there is no provided style.
        ret = None
      else:
        # Otherwise recurse on the current directory.
        ret = _FindYapfConfigFile(parent_dir, yapf_config_cache, top_dir)
    yapf_config_cache[fpath] = ret
    return ret

  depot_tools_path = os.path.dirname(os.path.abspath(__file__))
  yapf_tool = os.path.join(depot_tools_path, 'yapf')
  if sys.platform.startswith('win'):
    yapf_tool += '.bat'

  # If we couldn't find a yapf file we'll default to the chromium style
  # specified in depot_tools.
  chromium_default_yapf_style = os.path.join(depot_tools_path,
                                             YAPF_CONFIG_FILENAME)
  # Used for caching.
  yapf_configs = {}
  for f in python_diff_files:
    # Find the yapf style config for the current file, defaults to depot
    # tools default.
    _FindYapfConfigFile(f, yapf_configs, top_dir)

  # Turn on python formatting by default if a yapf config is specified.
  # This breaks in the case of this repo though since the specified
  # style file is also the global default.
  if python_flag is None:
    filtered_py_files = []
    for f in python_diff_files:
      if _FindYapfConfigFile(f, yapf_configs, top_dir) is not None:
        filtered_py_files.append(f)
  else:
    filtered_py_files = python_diff_files

  # Note: yapf still seems to fix indentation of the entire file
  # even if line ranges are specified.
  # See https://github.com/google/yapf/issues/499
  if not full and filtered_py_files:
    py_line_diffs = _ComputeDiffLineRanges(filtered_py_files, upstream_commit)

  # If we set this to 2, it means that we've failed the format check
  return_value = 0

  for f in filtered_py_files:
    yapf_config = _FindYapfConfigFile(f, yapf_configs, top_dir)
    if yapf_config is None:
      yapf_config = chromium_default_yapf_style

    cmd = [yapf_tool, '--style', yapf_config, f]

    has_formattable_lines = False
    if not full:
      # Only run yapf over changed line ranges.
      for diff_start, diff_len in py_line_diffs[f]:
        diff_end = diff_start + diff_len - 1
        # Yapf errors out if diff_end < diff_start but this
        # is a valid line range diff for a removal.
        if diff_end >= diff_start:
          has_formattable_lines = True
          cmd += ['-l', '{}-{}'.format(diff_start, diff_end)]
      # If all line diffs were removals we have nothing to format.
      if not has_formattable_lines:
        continue

    if diff or dry_run:
      cmd += ['--diff']
      # Will return non-zero exit code if non-empty diff.
      stdout = _RunCommand(cmd, error_ok=True, cwd=top_dir)
      if diff:
        output.write(stdout)
      elif len(stdout) > 0:
        return_value = 2
    else:
      cmd += ['-i']
      _RunCommand(cmd, cwd=top_dir)

  return return_value


def _DartFormat(dart_diff_files,
                output,
                top_dir=None,
                dry_run=False,
                diff=False):
  try:
    command = [dart_format.FindDartFmtToolInChromiumTree()]
    if not dry_run and not diff:
      command.append('-w')
    command.extend(dart_diff_files)

    stdout = _RunCommand(command, cwd=top_dir)
    if dry_run and stdout:
      output.write(stdout)
      return 2
  except dart_format.NotFoundError:
    print('Warning: Unable to check Dart code formatting. Dart SDK not '
          'found in this checkout. Files in other languages are still '
          'formatted.')
  return 0


def _GnFormat(gn_diff_files, output, top_dir=None, dry_run=False, diff=False):
  cmd = ['gn', 'format']
  if dry_run or diff:
    cmd.append('--dry-run')

  # If we set this to 2, it means that we've failed the format check
  return_value = 0

  for gn_diff_file in gn_diff_files:
    gn_ret = subprocess2.call(
        cmd + [gn_diff_file], shell=sys.platform == 'win32', cwd=top_dir)
    if dry_run and gn_ret == 2:
      return_value = 2  # Not formatted.
    elif diff and gn_ret == 2:
      # TODO this should compute and print the actual diff.
      output.write("This change has GN build file diff for " + gn_diff_file)
    elif gn_ret != 0:
      # For non-dry run cases (and non-2 return values for dry-run), a
      # nonzero error code indicates a failure, probably because the file
      # doesn't parse.
      raise Exception("gn format failed on " + gn_diff_file +
                      "\nTry running 'gn format' on this file manually.")
  return return_value


def _MetricsFormat(diff_files, output, top_dir=None, dry_run=False, diff=False):

  def _GetDirtyMetricsDirs(diff_files):
    xml_diff_files = [x for x in diff_files if _MatchingFileType(x, ['.xml'])]
    metrics_xml_dirs = [
        os.path.join('tools', 'metrics', 'actions'),
        os.path.join('tools', 'metrics', 'histograms'),
        os.path.join('tools', 'metrics', 'rappor'),
        os.path.join('tools', 'metrics', 'ukm')
    ]
    for xml_dir in metrics_xml_dirs:
      if any(file.startswith(xml_dir) for file in xml_diff_files):
        yield xml_dir

  # If we set this to 2, it means that we've failed the format check
  return_value = 0

  for xml_dir in _GetDirtyMetricsDirs(diff_files):
    tool_dir = os.path.join(top_dir, xml_dir)
    cmd = [
        'python',
        os.path.join(tool_dir, 'pretty_print.py'),
        '--non-interactive',
    ]
    if dry_run or diff:
      cmd.append('--diff')
    stdout = _RunCommand(cmd, cwd=top_dir)
    if diff:
      output.write(stdout)
    if dry_run and stdout:
      return_value = 2  # Not formatted.
  return return_value


def _MatchingFileType(file_name, extensions):
  return any([file_name.lower().endswith(ext) for ext in extensions])


def RunFormatters(change,
                  targets=None,
                  output_stream=sys.stdout,
                  full=None,
                  dry_run=False,
                  python=None,
                  javascript=False,
                  print_diff=False,
                  presubmit=False):
  """Runs auto-formatting tools (clang-format etc.) on the changelist."""
  CLANG_EXTS = ['.cc', '.cpp', '.h', '.m', '.mm', '.proto', '.java']
  GN_EXTS = ['.gn', '.gni', '.typemap']

  if javascript:
    CLANG_EXTS.extend(['.js', '.ts'])

  # Get the repo root
  top_dir = os.path.normpath(
      _RunGit(["rev-parse", "--show-toplevel"]).rstrip('\n'))

  # Handle target specification and selection of changed files to format
  if targets is not None and len(targets) != 0:
    # Convert any provided targets from being relative to the current directory
    # to being relative to the repository root. We want root-relative paths for
    # our targets so that they match what `git diff` returns, and we can filter
    # the set of files that we already have in the changelist for the targets.
    targets = [
        os.path.relpath(os.path.abspath(target), start=top_dir)
        for target in targets
    ]

  # git diff generates paths against the root of the repository. Change to that
  # directory so clang-format can find files even within subdirs.
  with MoveToDir(top_dir):
    upstream_commit = change.GetChangeBase()

    if not upstream_commit:
      raise Exception('Could not find base commit for this branch. '
                      'Are you in detached state?')

    diff_files = change.LocalPaths()
    # If we specify targets, we should filter to those
    if targets is not None and len(targets) != 0:
      # Selecting only files and directories should cover all of the cases that
      # we should lint/fix (symlinks, missing files, deleted entries, and other
      # arguments provided in error don't make sense for linting).
      target_files = frozenset([x for x in targets if os.path.isfile(x)])
      target_dirs = [x for x in targets if os.path.isdir(x)]

      # Filter to just paths named in the targets argument
      new_diff_files = set()
      for file_name in diff_files:
        if file_name in target_files:
          new_diff_files.add(file_name)
        else:
          # This implementation is based on the guess that there's few
          # targets, or they're explicit file refs
          for spec in target_dirs:
            if file_name.startswith(spec + os.path.sep):
              new_diff_files.add(file_name)
              break
      diff_files = new_diff_files

    # Filter out files deleted by this CL
    diff_files = [x for x in diff_files if os.path.isfile(x)]

    clang_diff_files = [
        x for x in diff_files if _MatchingFileType(x, CLANG_EXTS)
    ]
    python_diff_files = [x for x in diff_files if _MatchingFileType(x, ['.py'])]
    dart_diff_files = [x for x in diff_files if _MatchingFileType(x, ['.dart'])]
    gn_diff_files = [x for x in diff_files if _MatchingFileType(x, GN_EXTS)]

    # Set to 2 to signal to CheckPatchFormatted() that this patch isn't
    # formatted. This is used to block during the presubmit.
    return_value = 0

    if clang_diff_files:
      val = _ClangFormat(
          clang_diff_files,
          upstream_commit,
          output_stream,
          top_dir=top_dir,
          full=full,
          dry_run=dry_run,
          diff=print_diff)
      if val == 2:
        return_value = 2

    # Similar code to above, but using yapf on .py files rather than
    # clang-format on C/C++ files
    if python_diff_files and python is not False:
      val = _PythonFormat(
          python_diff_files,
          upstream_commit,
          output_stream,
          full=full,
          dry_run=dry_run,
          python_flag=python,
          diff=print_diff)
      if val == 2:
        return_value = 2

    # Dart's formatter does not have the nice property of only operating on
    # modified chunks, so hard code full.
    if dart_diff_files:
      val = _DartFormat(
          dart_diff_files,
          output_stream,
          top_dir=top_dir,
          dry_run=dry_run,
          diff=print_diff)
      if val == 2:
        return_value = 2

    # Format GN build files. Always run on full build files for canonical form.
    if gn_diff_files:
      val = _GnFormat(
          gn_diff_files,
          output_stream,
          top_dir=top_dir,
          dry_run=dry_run,
          diff=print_diff)
      if val == 2:
        return_value = 2

    # Skip the metrics formatting from the global presubmit hook. These files
    # have a separate presubmit hook that issues an error if the files need
    # formatting, whereas the top-level presubmit script merely issues a
    # warning. Formatting these files is somewhat slow, so it's important not
    # to duplicate the work.
    if not presubmit:
      val = _MetricsFormat(
          diff_files,
          output_stream,
          top_dir=top_dir,
          dry_run=dry_run,
          diff=print_diff)
      if val == 2:
        return_value = 2

  return return_value
