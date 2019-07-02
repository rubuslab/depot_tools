# Copyright 2019 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import recipe_test_api

class PresubmitTestApi(recipe_test_api.RecipeTestApi):

  def __call__(self, clear_pythonpath=False, timeout_s=480,
               vpython_spec_path=None):
    ret = self.test(None)
    ret.properties = {
        '$depot_tools/presubmit': {
            'clear_pythonpath': clear_pythonpath,
            'timeout_s': timeout_s,
            'vpython_spec_path': vpython_spec_path,
        },
    }

    return ret
