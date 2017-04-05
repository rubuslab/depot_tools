#!/usr/bin/env python
# Copyright 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Splits a branch into smaller branches and uploads CLs."""

import git_cl
import subprocess2
import sys
import optparse
import os
import owners_finder

import git_common as git

TMP_FILE = 'git_split_cl_tmp_file.txt'

def ReadFile(file_path):
  with open(file_path, 'r') as f:
    content = f.read()
  return content

def WriteFile(file_path, content):
  with open(file_path, 'wb') as f:
    f.write(content)
    f.write('\n')

def EnsureInGitRepository():
  # This throws an exception if the current directory is not a git repository.
  git.run('branch')

def CreateBranchForFile(branch_prefix, file_path):
  branch = branch_prefix + '_' + os.path.splitext(os.path.basename(
      file_path))[0]
  for i in range(0, 10):
    try:
      git.run('new-branch', branch + (str(i) if i != 0 else ''))
      return
    except subprocess2.CalledProcessError:
      pass
  print 'Unable to find an unused branch name for ' + file_path + '.'
  sys.exit(1)

def FormatDescriptionOrComment(txt, root, file_path):
  txt = txt.replace('$file_path', os.path.relpath(file_path, root))
  txt = txt.replace('$file_name', os.path.basename(file_path))
  return txt

def UploadClForFile(root, main_branch, file_path, author, description, comment):
  # Create a branch for changes to |file_path|.
  CreateBranchForFile(main_branch, file_path)
  git.run('checkout', main_branch, file_path)

  # Commit changes.
  WriteFile(TMP_FILE, FormatDescriptionOrComment(description, root, file_path))
  git.run('commit', '-F', TMP_FILE)

  # Find an owner.
  author = git.run('config', 'user.email').strip() or None
  owners_finder_instance = owners_finder.OwnersFinder(
      [file_path], root, None, None, fopen=file, os_path=os.path)
  owner = owners_finder_instance.owners_queue[0]
  if owner == author:
    owner = owners_finder_instance.owners_queue[1]
  assert owner != author

  # Upload a CL.
  git.run('cl', 'upload', '-f', '--cq-dry-run', '-r', owner, '--send-mail')
  if comment:
    cl = git_cl.Changelist()
    cl.AddComment(FormatDescriptionOrComment(comment, root, file_path))

  print 'Uploaded CL for ' + file_path + '.'

def main():
  parser = optparse.OptionParser()
  parser.add_option("-d", "--description", dest="description_file",
                    help="A text file containing a CL description. ")
  parser.add_option("-c", "--comment", dest="comment_file",
                    help="A text file containing a CL comment.")

  options, _ = parser.parse_args()

  if not options.description_file:
    parser.error('No --description flag specified.')

  description = ReadFile(options.description_file)

  comment = None
  if options.comment_file:
    comment = ReadFile(options.comment_file)

  try:
    EnsureInGitRepository();

    cl = git_cl.Changelist()
    change = cl.GetChange(cl.GetCommonAncestorWithUpstream(), None)
    root = change.RepositoryRoot()
    file_paths = [f.LocalPath() for f in change.AffectedFiles()]

    if not file_paths:
      print 'Cannot split an empty CL.'
      sys.exit(1)

    main_branch = git.current_branch()
    print 'Will split current branch (' + main_branch +') in multiple CLs.\n'

    author = git.run('config', 'user.email').strip() or None

    for file_path in file_paths:
      UploadClForFile(root, main_branch, file_path, author, description,
                      comment)

    git.run('checkout', main_branch)

  except subprocess2.CalledProcessError as cpe:
    sys.stderr.write(cpe.stderr)
    return 1
  return 0

if __name__ == "__main__":  # pragma: no cover
  try:
    sys.exit(main())
  except KeyboardInterrupt:
    sys.stderr.write('interrupted\n')
    sys.exit(1)

