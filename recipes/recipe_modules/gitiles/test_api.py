# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import base64
import hashlib

from recipe_engine import recipe_test_api


class GitilesTestApi(recipe_test_api.RecipeTestApi):

  def make_refs_test_data(self, *refs):
    return {ref: None for ref in refs}

  def refs(self, step_name, *refs):
    return self.m.url.json(step_name, self.make_refs_test_data(*refs))

  def make_log_test_data(self, s, n=3, cursor=None):
    result = {
        'log': [
            self.make_commit_gitiles_dict(
                commit='fake %s hash %d' % (s, i),
                msg='fake %s msg %d' % (s, i),
                new_files=['%s.py' % (chr(i + ord('a')))],
                email='fake_%s@fake_%i.email.com' % (s, i),
            )
            for i in xrange(n)
        ],
    }
    if cursor:
      result['next'] = cursor
    return result

  def logs(self, step_name, s, n=3):
    return self.m.url.json(step_name, self.make_log_test_data(s, n=n))

  def make_commit_gitiles_dict(self, commit, msg, new_files, email=None):
    """Constructs fake Gitiles commit JSON test output.

    This data structure conforms to the JSON response that Gitiles provides when
    a commit is queried. For example:
    https://chromium.googlesource.com/chromium/src/+/875b896a3256c5b86c8725e81489e99ea6c2b4c9?format=json

    Args:
      commit (str): The fake commit hash.
      msg (str): The commit message.
      new_files (list): If not None, a list of filenames (str) to simulate being
          added in this commit.
      email: if not None, a proper email with '@' in it to be used for
          committer's and author's emails.
    Returns: (raw_io.Output) A simulated Gitiles fetch 'json' output.
    """
    if email is None:
      name = 'Test Author'
      email = 'testauthor@fake.chromium.org'
    else:
      assert '@' in email
      name = email.split('@')[0]
    d = {
        'commit': self.make_hash(commit),
        'tree': self.make_hash('tree', commit),
        'parents': [self.make_hash('parent', commit)],
        'author': {
            'name': name,
            'email': email,
            'time': 'Mon Jan 01 00:00:00 2015',
        },
        'committer': {
            'name': name,
            'email': email,
            'time': 'Mon Jan 01 00:00:00 2015',
        },
        'message': msg,
        'tree_diff': [],
    }
    if new_files:
      d['tree_diff'].extend({
          'type': 'add',
          'old_id': 40 * '0',
          'old_mode': 0,
          'new_id': self.make_hash('file', f, commit),
          'new_mode': 33188,
          'new_path': f,
      } for f in new_files)
    return d

  def commit(self, step_name, commit, msg, new_files, email=None):
    return self.m.url.json(
        step_name,
        self.make_commit_gitiles_dict(commit, msg, new_files, email=email))

  def make_encoded_file(self, data):
    return base64.b64encode(data)

  def encoded_file(self, step_name, content):
    return self.m.url.text(step_name, self.make_encoded_file(content))

  def make_hash(self, *bases):
    return hashlib.sha1(':'.join(bases)).hexdigest()
