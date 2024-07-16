# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import copy
import os
import re
import sys

from dataclasses import dataclass
from typing import Dict, List, Mapping, Optional
from unittest import mock
import unittest

from scm import GitConfigScope

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import scm




def mock_GIT(test: unittest.TestCase,
             config: Optional[Dict[str, List[str]]] = None,
             branchref: Optional[str] = None):
    """Installs fakes/mocks for scm.GIT so that:

      * Initial git config is set to `config`.
      * All Git configuration operations ignore 'scope' and update the config
        state in memory.
      * GetBranch will just return a fake branchname starting with the value of
        branchref.
      * git_new_branch.create_new_branch will be mocked to update the value
        returned by GetBranch.

    NOTE: The dependency on git_new_branch.create_new_branch seems pretty
    circular - this functionality should probably move to scm.GIT?

    You will need to call mock.stopall() in tearDown after using this.
    """
    _branchref = [branchref or 'refs/heads/main']

    initial_state = {}
    if config is not None:
        initial_state['local'] = config

    mock.patch('scm.GIT._new_config_state',
               side_effect=lambda root: scm.GitConfigStateTest(initial_state)).start()
    mock.patch('scm.GIT.GetBranchRef',
               side_effect=lambda _root: _branchref[0]).start()

    def _newBranch(branchref):
        _branchref[0] = branchref

    mock.patch('git_new_branch.create_new_branch',
               side_effect=_newBranch).start()

    test.addCleanup(scm.GIT._CONFIG_CACHE.clear)
