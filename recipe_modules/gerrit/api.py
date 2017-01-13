# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
import json
import urllib

from recipe_engine import recipe_api

class GerritApi(recipe_api.RecipeApi):
  """Module for interact with gerrit endpoints"""

  def __call__(self, name, cmd, infra_step=True, **kwargs):
    """Wrapper for easy calling of gerrit_utils steps."""
    assert isinstance(cmd, (list, tuple))
    prefix = 'gerrit '

    kwargs.setdefault('env', {})
    kwargs['env'].setdefault('PATH', '%(PATH)s')
    kwargs['env']['PATH'] = self.m.path.pathsep.join([
        kwargs['env']['PATH'], str(self._module.PACKAGE_REPO_ROOT)])

    return self.m.python(prefix + name,
                         self.package_repo_resource('gerrit_client.py'),
                         cmd,
                         infra_step=infra_step,
                         **kwargs)

  # Implementation using a gerrit_client.py like recipe_modules/gitiles,
  # but is it too much overhead and complexity?
  def create_gerrit_branch(self, host, project, branch, commit):
    """
    Create a new branch from given project and commit
    https://gerrit-review.googlesource.com/Documentation/rest-api-projects.html#create-branch

    Returns:
      the ref of the branch created
    """
    path = 'projects/%s/branches/%s' % (urllib.quote_plus(project),
                                        urllib.quote_plus(branch))
    body = {'revision': commit}
    step_result = self._make_gerrit_request(step_name='create_gerrit_branch',
                              host=host,
                              path=path,
                              request_type='PUT',
                              json_file=self.m.json.output(),
                              body=json.dumps(body),
                              dry_run=True)
    ref = step_result.json.output.get('ref')
    return ref

  def get_gerrit_branch(self, host, project, branch):
    """
    Get a new branch from given project and commit
    https://gerrit-review.googlesource.com/Documentation/rest-api-projects.html#get-branch

    Returns:
      the revision of the branch
    """
    path = 'projects/%s/branches/%s' % (urllib.quote_plus(project),
                                        urllib.quote_plus(branch))
    step_result = self._make_gerrit_request(step_name='get_gerrit_branch',
                              host=host,
                              path=path,
                              request_type='GET',
                              json_file=self.m.json.output(),
                              dry_run=True)
    revision = step_result.json.output.get('revision')
    return revision

  def _make_gerrit_request(self, step_name, host, path, request_type,
                           json_file, dry_run=False, body=None, **kwargs):
    args = [
        '--host', host,
        '--path', path,
        '--request_type', request_type,
        '--json_file', json_file,
    ]
    if body:
      args.extend(['--body', body])
    if dry_run:
      args.extend(['--dry_run', True])
    result = self(
        step_name, args, **kwargs)
    return result