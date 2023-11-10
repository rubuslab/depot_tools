#!/usr/bin/env python3
# Copyright 2023 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import gclient_eval
import gclient_paths
import gclient_scm
import gclient_utils
import os
import sys

DEPOT_TOOLS_DIR = os.path.dirname(os.path.abspath(os.path.realpath(__file__)))


def main():
    # expect DEPS file in cwd.
    filepath = 'DEPS'
    if not os.path.exists(filepath):
        return 1

    with open(filepath) as f:
        deps_content = f.read()
    local_scope = gclient_eval.Parse(deps_content, filepath, {},
                                     {'checkout_linux': True})
    cipd = {}
    for key, dep in local_scope['deps'].items():
        if 'deb_type' not in dep or dep['deb_type'] != 'cipd':
            pass
        # TODO: evaluate condition and see if needed
        cipd[key] = dep

    # TODO: cipd ensure with local cachine (home dir, e.g. ~/.cache/cipd)

    # hooks - evaluate too
    for hook in local_scope['hooks']:
        pass

    # TODO -> needs to be done recursively for recuredeps

    import pdb
    pdb.set_trace()


if '__main__' == __name__:
    sys.exit(main())
