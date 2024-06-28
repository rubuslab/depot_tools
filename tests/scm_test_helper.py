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


@dataclass
class GitConfigStateTest(scm.GitConfigState):
    default: Optional[Dict[str, List[str]]] = None

    def _load_config(self) -> Mapping[str, List[str]]:
        if self.default is None:
            return {}
        return copy.deepcopy(self.default)

    def _set_config(self, key: str, value: str, append: bool,
                    scope: GitConfigScope):
        cfg = self._maybe_load_config()
        cur = cfg.get(key)
        if cur is None or len(cur) == 1:
            if append:
                cfg[key] = (cur or []) + [value]
            else:
                cfg[key] = [value]
            return
        raise ValueError(f'GitConfigStateTest: Cannot set key {key} '
                         f'- current value {cur!r} is multiple.')

    def _set_config_multi(self, key: str, value: str, append: bool,
                          value_pattern: Optional[str], scope: GitConfigScope):
        cfg = self._maybe_load_config()
        cur = cfg.get(key)
        if value_pattern is None or cur is None:
            if append:
                cfg[key] = (cur or []) + [value]
            else:
                cfg[key] = [value]
            return

        pat = re.compile(value_pattern)
        newval = [v for v in cur if pat.match(v)]
        newval.append(value)
        cfg[key] = newval

    def _unset_config(self, key: str, scope: GitConfigScope):
        cfg = self._maybe_load_config()
        cur = cfg.get(key)
        if cur is None or len(cur) == 1:
            del cfg[key]
            return
        raise ValueError(f'GitConfigStateTest: Cannot unset key {key} '
                         f'- current value {cur!r} is multiple.')

    def _unset_config_multi(self, key: str, value_pattern: Optional[str],
                            scope: GitConfigScope):
        cfg = self._maybe_load_config()
        if value_pattern is None:
            del cfg[key]
            return

        cur = cfg.get(key)
        if cur is None:
            del cfg[key]
            return

        pat = re.compile(value_pattern)
        cfg[key] = [v for v in cur if not pat.match(v)]


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

    mock.patch('scm.GIT._new_config_state',
               side_effect=lambda root: GitConfigStateTest(root, default=config)
               ).start()
    mock.patch('scm.GIT.GetBranchRef',
               side_effect=lambda _root: _branchref[0]).start()

    def _newBranch(branchref):
        _branchref[0] = branchref

    mock.patch('git_new_branch.create_new_branch',
               side_effect=_newBranch).start()

    test.addCleanup(scm.GIT._CONFIG_CACHE.clear)
