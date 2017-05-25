#!/usr/bin/env python
# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Splits a branch into smaller branches and uploads CLs."""

import git_cl
import git_footers
import optparse
import os
import owners_finder
import subprocess2
import sys
import tempfile

import git_common as git

# Map where keys are file paths and values are booleans indicating whether the
# files exist.
FILE_EXISTS_MAP = {}

def FileExists(file_path):
  if file_path not in FILE_EXISTS_MAP:
    FILE_EXISTS_MAP[file_path] = os.path.isfile(file_path)
  return FILE_EXISTS_MAP[file_path]

def ReadFile(file_path):
  with open(file_path, 'r') as f:
    content = f.read()
  return content

def EnsureInGitRepository():
  # This throws an exception if the current directory is not a git repository.
  git.run('branch')

def CreateBranchForDirectory(branch_prefix, directory):
  branch = branch_prefix + '_' + directory.replace(os.path.sep, '_')
  for i in range(0, 10):
    try:
      git.run('new-branch', branch + (str(i) if i != 0 else ''))
      return
    except subprocess2.CalledProcessError:
      pass
  print 'Unable to find an unused branch name for ' + directory + '.'
  sys.exit(1)

def FormatDescriptionOrComment(txt, directory):
  # Always use / as a path separator in the CL description and comment.
  return txt.replace('$directory', directory.replace(os.path.sep, '/'))

def AddUploadedByGitClSplitToDescription(description):
  split_footers = git_footers.split_footers(description)
  lines = split_footers[0] + ['This CL was uploaded by git cl split.']
  if split_footers[1]:
    lines += [''] + split_footers[1]
  return '\n'.join(lines)

def UploadCl(repository_root, main_branch, directory, files, author,
             description, comment):
  # Create a branch with all changes to files in |files|.
  CreateBranchForDirectory(main_branch, directory)
  for f in files:
    if f.Action() == 'D':
      git.run('rm', f.AbsoluteLocalPath())
    else:
      git.run('checkout', main_branch, '--', f.AbsoluteLocalPath())

  # Commit changes.
  with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
    tmp_file.write(FormatDescriptionOrComment(description, directory))
    # Close the file to let git open it at the next line.
    tmp_file.close()
    git.run('commit', '-F', tmp_file.name)
    os.remove(tmp_file.name)

  # Find owners other than the CL author.
  owners_finder_instance = owners_finder.OwnersFinder(
      [f.LocalPath() for f in files], repository_root, None, file, os.path,
      verbose=False)
  owners_finder_instance.deselect_owner(author)
  while owners_finder_instance.unreviewed_files:
    owners_finder_instance.select_owner(owners_finder_instance.owners_queue[0])

  # Upload a CL.
  git.run('cl', 'upload', '-f', '--cq-dry-run', '-r',
          ','.join(owners_finder_instance.selected_owners), '--send-mail')
  if comment:
    cl = git_cl.Changelist()
    cl.AddComment(FormatDescriptionOrComment(comment, directory))

  print 'Uploaded CL for ' + directory + '.'

# Returns a map:
#    Key: Path to a directory containing an OWNERS file
#    Value: List of files from |files| for which the closest OWNERS file is the
#       one in the directory from the key.
def GetFilesSplitByOwners(repository_root, files):
  files_split_by_owners = {}
  for f in files:
    owners_file_directory = os.path.dirname(f.AbsoluteLocalPath())
    while owners_file_directory.startswith(repository_root):
      if FileExists(os.path.join(owners_file_directory, 'OWNERS')):
        break
      owners_file_directory = os.path.dirname(owners_file_directory)
    owners_file_directory_relative = os.path.relpath(
        owners_file_directory, repository_root)
    if not owners_file_directory_relative in files_split_by_owners:
      files_split_by_owners[owners_file_directory_relative] = []
    files_split_by_owners[owners_file_directory_relative].append(f)
  return files_split_by_owners

def SplitCl(parser, args):
  parser.add_option("-d", "--description", dest="description_file",
                    help="A text file containing a CL description. ")
  parser.add_option("-c", "--comment", dest="comment_file",
                    help="A text file containing a CL comment.")
  options, _ = parser.parse_args(args)

  if not options.description_file:
    parser.error('No --description flag specified.')

  description = AddUploadedByGitClSplitToDescription(
      ReadFile(options.description_file))
  comment = ReadFile(options.comment_file) if options.comment_file else None

  try:
    EnsureInGitRepository();

    cl = git_cl.Changelist()
    change = cl.GetChange(cl.GetCommonAncestorWithUpstream(), None)
    affected_files = change.AffectedFiles()

    if not affected_files:
      print 'Cannot split an empty CL.'
      return 1

    repository_root = change.RepositoryRoot()
    author = git.run('config', 'user.email').strip() or None
    main_branch = git.current_branch()
    files_split_by_owners = GetFilesSplitByOwners(
        repository_root, affected_files)

    print ('Will split current branch (' + main_branch +') in ' +
           str(len(files_split_by_owners)) + ' CLs.\n')

    for directory, files in files_split_by_owners.iteritems():
      UploadCl(repository_root, main_branch, directory, files, author,
               description, comment)

    # Go back to the original branch.
    git.run('checkout', main_branch)

  except subprocess2.CalledProcessError as cpe:
    sys.stderr.write(cpe.stderr)
    return 1
  return 0
