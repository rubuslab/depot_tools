#!/usr/bin/env python3
# Copyright 2024 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Upload a chain of cherry picks as a Gerrit change.

Gerrit only recognizes cherry picks via its REST API. This tool is
meant to be a substitute for local git cherrypicks.
"""

import argparse
import sys

import gclient_utils
import gerrit_utils
import git_common
import git_footers


def create_commit_message(orig_message, bug=None):
    """Returns a commit message for the cherry picked CL."""
    orig_message_lines = orig_message.splitlines()
    subj_line = orig_message_lines[0]
    new_message = (f'Cherry pick "{subj_line}"\n\n'
                   "Original change's description:\n")
    for line in orig_message_lines:
        new_message += f'> {line}\n'
    if bug:
        new_message += f'\nBug: {bug}\n'
    return new_message


# TODO(b/341792235): Add metrics.
def main(argv):
    if gclient_utils.IsEnvCog():
        print('gerrit-cp command is not supported in non-git environment.',
              file=sys.stderr)
        return 1

    parser = argparse.ArgumentParser()
    # TODO(XXX): make sure these are mandatory.
    parser.add_argument('--host', help='Gerrit host to upload changes to.')
    parser.add_argument('--branch', help='Gerrit branch to upload changes to.')
    parser.add_argument('--bug',
                        help='Bug to add to the description of each change.')
    parser.add_argument('-c',
                        '--commit',
                        nargs='+',
                        help='Commit(s) to cherrypick.')
    # TODO(XXX): maybe accept change ids instead? or change/ps
    args = parser.parse_args(argv)

    # Gerrit needs a change ID for each commit we cherry pick.
    change_ids_to_message = {}
    for commit in args.commit:
        # Validate it's a real commit.
        git_common.hash_one(commit)
        message = git_common.run('show', '-s', '--format=%B', 'hash').strip()
        if change_id := git_footers.get_footer_change_id(message):
            change_ids_to_message[change_id] = message
            break

        # Gerrit changes should all have a change ID associated with them.
        # If we can't find one in the commit description then it
        # is not a submitted Gerrit change.
        raise RuntimeError(f'Change ID not found for {commit}')

    # Gerrit only supports cherry picking one commit per change, so we have
    # to create a chain of CLs and cherry pick each commit individually.
    parent_change_id = None
    for change_id, orig_message in change_ids_to_message.items():
        # Create a cherry pick first, then rebase. If we try creating a chained
        # CL then cherry picking in a followup patchset, it will lose its
        # relation.
        message = create_commit_message(orig_message, args.bug)
        new_change_info = gerrit_utils.CherryPick(args.host,
                                                  change_id,
                                                  args.branch,
                                                  message=message)
        new_change_id = new_change_info['change_id']
        gerrit_utils.RebaseChange(args.host, new_change_id, parent_change_id)
        orig_subj_line = orig_message.splitlines()[0]
        print(f'Created cherry pick of {orig_subj_line} at '
              f'https://{args.host}/q/{change_id}')
        parent_change_id = new_change_id

    return 0


if __name__ == '__main__':
    try:
        sys.exit(main(sys.argv[1:]))
    except KeyboardInterrupt:
        sys.stderr.write('interrupted\n')
        sys.exit(1)
