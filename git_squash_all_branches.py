#!/usr/bin/env python3
# Copyright 2024 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""
Tool to squash all branches and their downstream branches.
"""

import argparse
import collections
import git_common as git
import logging
import sys


# Returns the list of branches that have diverged from their respective upstream branch.
def get_diverged_branches(tree):
    diverged_branches = []

    for branch, upstream_branch in tree.items():
        if git.hash_one(upstream_branch) != git.hash_one(
                git.get_or_create_merge_base(branch)):
            diverged_branches.append(branch)

    return diverged_branches


# Returns a dictionary that contains the hash of every branch before the
# squashing started.
def get_initial_hashes(tree):
    initial_hashes = {}
    for branch in tree:
        initial_hashes[branch] = git.hash_one(branch)
    initial_hashes[git.upstream_default()] = git.hash_one(
        git.upstream_default())
    return initial_hashes


# Returns a dictionary that contains the downstream branches of every parent branch.
def get_downstream_branches(tree):
    downstream_branches = collections.defaultdict(list)
    for branch, upstream_branch in tree.items():
        downstream_branches[upstream_branch].append(branch)
    return downstream_branches


def squash_branch(branch, initial_hashes):
    print("Squashing branch %s." % branch)
    assert initial_hashes[branch] == git.hash_one(branch)

    upstream_branch = git.upstream(branch)
    old_upstream_branch = initial_hashes[upstream_branch]

    # Because the branch's upstream has potentially changed from squashing it,
    # the current branch is rebased on top of the new upstream.
    logging.debug('Rebasing %s.' % branch)
    git.run("rebase", "--onto", upstream_branch, old_upstream_branch, branch,
            "--update-refs")

    # Then squashing is done.
    logging.debug('Squashing %s' % branch)
    git.run("checkout", branch)
    git.squash_current_branch()


# Squashes all branches that are part of the subtree starting at `branch`.
def squash_subtree(branch, initial_hashes, downstream_branches):
    # The upstream default never has to be squashed (e.g. origin/main).
    if branch != git.upstream_default():
        squash_branch(branch, initial_hashes)

    # Recurse on downstream branches, if any.
    for downstream_branch in downstream_branches[branch]:
        squash_subtree(downstream_branch, initial_hashes, downstream_branches)


def main(args=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('--verbose', '-v', action='store_true')
    parser.add_argument('--ignore-no-upstream', action='store_true')
    parser.add_argument(
        '--branch',
        '-b',
        type=str,
        default=git.upstream_default(),
        help=
        'The name of the branch who\'s subtree must be squashed. Defaults to `origin/main`.'
    )
    opts = parser.parse_args(args)

    if opts.verbose:  # pragma: no cover
        logging.getLogger().setLevel(logging.DEBUG)

    if git.is_dirty_git_tree('squash-all-branches'):
        return 1

    branches_without_upstream, tree = git.get_branch_tree()

    if not opts.ignore_no_upstream and branches_without_upstream:
        print(
            "This tool can't be used if some branches don't have an upstream. Pass --ignore-no-upstream to ignore this check."
        )
        return 1

    diverged_branches = get_diverged_branches(tree)
    if (diverged_branches):
        print(
            "This tool can't be used if some branches have diverged from their upstream."
        )
        for diverged_branch in diverged_branches:
            print(diverged_branch)
        return 1

    initial_hashes = get_initial_hashes(tree)
    downstream_branches = get_downstream_branches(tree)

    return_branch = git.current_branch()
    squash_subtree(opts.branch, initial_hashes, downstream_branches)
    git.run("checkout", return_branch)


if __name__ == '__main__':  # pragma: no cover
    try:
        sys.exit(main(sys.argv[1:]))
    except KeyboardInterrupt:
        sys.stderr.write('interrupted\n')
        sys.exit(1)
