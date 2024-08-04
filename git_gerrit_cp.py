#!/usr/bin/env python3
# Copyright 2024 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Utility for uploading a chain of cherry picks to Gerrit."""

import argparse
import sys

import gclient_utils
import gerrit_util
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
    parser.add_argument(
        '--host',
        required=True,
        help='Gerrit host, e.g. chromium-review.googlesource.com')
    parser.add_argument('--branch',
                        required=True,
                        help='Gerrit branch, e.g. refs/heads/main')
    parser.add_argument('--bug',
                        help='Bug to add to the description of each change.')
    parser.add_argument('-c',
                        '--commit',
                        nargs='+',
                        help='Commit(s) to cherry pick.')
    args = parser.parse_args(argv)

    # Gerrit needs a change ID for each commit we cherry pick.
    change_ids_to_message = {}
    for commit in args.commit:
        message = git_common.run('show', '-s', '--format=%B', commit).strip()
        if change_id := git_footers.get_footer_change_id(message):
            change_ids_to_message[change_id[0]] = message
            continue
        raise RuntimeError(f'Change ID not found for {commit}')

    print(f'Creating chain of {len(change_ids_to_message)} cherry pick(s)...')

    # Gerrit only supports cherry picking one commit per change, so we have
    # to cherry pick each commit individually and create a chain of CLs.
    parent_change_num = None
    for change_id, orig_message in change_ids_to_message.items():
        message = create_commit_message(orig_message, args.bug)

        # Create a cherry pick first, then rebase. If we create a chained CL
        # then cherry pick, the change will lose its relation to the parent.
        new_change_info = gerrit_util.CherryPick(args.host,
                                                 change_id,
                                                 args.branch,
                                                 message=message)
        new_change_id = new_change_info['change_id']
        new_change_num = new_change_info['_number']

        if parent_change_num:
            gerrit_util.RebaseChange(args.host, new_change_id,
                                     parent_change_num)
        parent_change_num = new_change_num

        orig_subj_line = orig_message.splitlines()[0]
        print(f'Created cherry pick of "{orig_subj_line}": '
              f'https://{args.host}/q/{new_change_id}')

    return 0


if __name__ == '__main__':
    try:
        sys.exit(main(sys.argv[1:]))
    except KeyboardInterrupt:
        sys.stderr.write('interrupted\n')
        sys.exit(1)
