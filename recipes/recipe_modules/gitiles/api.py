# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import base64

from recipe_engine import recipe_api


class Gitiles(recipe_api.RecipeApi):
  """Module for polling a git repository using the Gitiles web interface."""

  def _fetch_json(self, url, step_name, default_test_data, add_log=True):
    """Fetches JSON data from Gitiles.

    Arguments:
      add_log: if True, will spill out json into log.
    """
    return self.m.url.get_json(
        url,
        step_name=step_name,
        log=add_log,
        strip_prefix=self.m.url.GERRIT_JSON_PREFIX,
        default_test_data=default_test_data,
    ).output

  def refs(self, url, step_name=None, default_test_data=None):
    """Returns a list of refs in the remote repository.

    Arguments:
      default_test_data (dict): Default step test data, if none is supplied.
          Should be formatted like test API's "make_refs_test_data".
    """
    output = self._fetch_json(
        self.m.url.join(url, '+refs'),
        step_name or 'refs',
        default_test_data)

    refs = sorted(str(ref) for ref in output)
    self.m.step.active_result.presentation.logs['refs'] = refs
    return refs

  def log(self, url, ref, limit=None, cursor=None, step_name=None,
          default_test_data=None):
    """Returns the most recent commits under the given ref with properties.

    Args:
      url (str): URL of the remote repository.
      ref (str): Name of the desired ref (see Gitiles.refs).
      limit (int): Number of commits to limit the fetching to.
        Gitiles does not return all commits in one call; instead paging is
        used. 0 implies to return whatever first gerrit responds with.
        Otherwise, paging will be used to fetch at least this many
        commits, but all fetched commits will be returned.
      cursor (str or None): The paging cursor used to fetch the next page.
      step_name (str): Custom name for this step (optional).
      default_test_data (dict): Default step test data, if none is supplied.
          Should be formatted like test API's make_log_test_data".

    Returns: (commits, cursor).
      commits (list): A list of commits (as Gitiles dict structure) in reverse
          chronological order. The number of commits may be higher than limit
          argument.
      cursor (str or None): a string that can be used for subsequent calls to
          log for paging. If None, signals that there are no more commits to
          fetch.
    """
    limit = limit or 0
    step_name = step_name or 'gitiles log: %s' % (ref,)

    assert limit >= 0
    commits = []
    with self.m.step.nest(step_name) as nested_step:
      # Loop until we have exhausted our limit.
      while True:
        url = self.m.url.join(url, '+log/%s' % ref)
        if cursor:
          url += '?s=%s' % (cursor,)
          iter_name = '%s...' % (cursor,)
        else:
          iter_name = 'initial'

        output = self._fetch_json(
            url,
            iter_name,
            default_test_data)

        # The first commit in `output` is not necessarily the parent of the
        # last commit in result so far!  This is because log command can be done
        # on one file object, for example:
        # https://gerrit.googlesource.com/gitiles/+log/1c21279f337da8130/COPYING
        #
        # Even when getting log for the whole repository, there could be merge
        # commits.
        commits.extend(output['log'])
        cursor = output.get('next')

        if not cursor or (limit-len(commits)) <= 0:
          break

    nested_step.presentation.step_text = (
        '<br />%d commits fetched' % len(commits))
    return commits, cursor

  def commit_log(self, url, commit, step_name=None, default_test_data=None):
    """Returns: (dict) the Gitiles commit log structure for a given commit.

    Args:
      url (str): The base repository URL.
      commit (str): The commit hash.
      step_name (str): If not None, override the step name.
      default_test_data (dict): Default step test data, if none is supplied.
          Should be formatted like test API's "make_commit_gitiles_dict".
    """
    return self._fetch_json(
        '%s/+/%s' % (url, commit),
        step_name or 'commit log: %s' % commit,
        default_test_data)

  def download_file(self, repository_url, file_path, branch='master',
                    step_name=None, default_test_data=None):
    """Downloads raw file content from a Gitiles repository.

    Args:
      repository_url (str): Full URL to the repository.
      branch (str): Branch of the repository.
      file_path (str): Relative path to the file from the repository root.
      step_name (str): Custom name for this step (optional).
      default_test_data (str or None): Default step test data, if none is
          supplied. Should be formatted like test API's "make_encoded_file".

    Returns:
      Raw file content.
    """
    fetch_url = self.m.url.join(repository_url, '+/%s/%s' % (branch, file_path))
    output = self.m.url.get_text(
        fetch_url,
        step_name or 'fetch %s:%s' % (branch, file_path,),
        default_test_data=default_test_data).output
    return base64.b64decode(output)
