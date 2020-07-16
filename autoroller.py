import base64
import json
import subprocess
import urllib.parse
import urllib.request


import gerrit_util


JSON_PREFIX_LEN = 4


auth = gerrit_util.CookiesAuthenticator()


class Repo:
  def __init__(self, name, git_url):
    self.name = name
    self.git_url = git_url
    self.host = urllib.parse.urlparse(self.git_url).netloc
    self.head_revision = self._get_head_revision()
    auth = gerrit_util.CookiesAuthenticator()
    self._config_cache = {}

  def __str__(self):
    return f'Repo({self.name})'

  __repr__ = __str__

  def __hash__(self):
    return hash(self.name)

  def __eq__(self, repo):
    return self.name == repo.name

  def _get_head_revision(self):
    url = f'{self.git_url}/+/HEAD?format=json'
    request = urllib.request.Request(
        url, headers={'Authorization': auth.get_auth_header(self.host)})
    with urllib.request.urlopen(request) as response:
      data = response.read()[JSON_PREFIX_LEN:]
      info = json.loads(data)
      return info['commit']

  def get_config(self, revision='HEAD'):
    if revision in self._config_cache:
      return self._config_cache[revision]
    url = f'{self.git_url}/+/{revision}/infra/config/recipes.cfg?format=text'
    request = urllib.request.Request(
        url, headers={'Authorization': auth.get_auth_header(self.host)})
    with urllib.request.urlopen(request) as response:
      b64_data = response.read()
      json_data = base64.b64decode(b64_data)
      config = json.loads(json_data)
    self._config_cache[revision] = config
    return config

  def get_deps(self, revision='HEAD'):
    deps = self.get_config(revision).get('deps', {})
    return {
        Repo(dep_name, dep_info['url']): dep_info['revision']
        for dep_name, dep_info in deps.items()
    }


def dfs(start, visited, toposorted):
  """Expand from start and return nodes in the order visited."""
  visited.add(start)
  for dep in start.get_deps():
    if dep not in visited:
      visited.add(dep)
      dfs(dep, visited, toposorted)
  toposorted.append(start)


def toposort(repos):
  """Sort repos in topological order."""
  repos = set(repos)
  visited = set()
  toposorted = []
  while repos:
    repo = repos.pop()
    if repo in visited:
      continue
    dfs(repo, visited, toposorted)
  return toposorted


repos = [
  Repo('infra', 'https://chromium.googlesource.com/infra/infra.git'),
  Repo('build', 'https://chromium.googlesource.com/chromium/tools/build.git'),
  Repo(
      'depot_tools',
      'https://chromium.googlesource.com/chromium/tools/depot_tools.git'),
  Repo(
      'recipe_engine',
      'https://chromium.googlesource.com/infra/luci/recipes-py.git'),
  Repo(
      'chrome_release',
      'https://chrome-internal.googlesource.com/chrome/tools/release/scripts.git'),
  Repo(
      'build_limited_scripts_slave',
      'https://chrome-internal.googlesource.com/chrome/tools/build_limited/scripts/slave.git'),
  Repo(
      'chromiumos_config',
      'https://chromium.googlesource.com/chromiumos/config'),
  Repo(
      'chromiumos_proto',
      'https://chromium.googlesource.com/chromiumos/infra/proto'),
  Repo(
      'chromeos',
      'https://chromium.googlesource.com/chromiumos/infra/recipes'),
]

new_revisions = {}

for repo in toposort(repos):
  # This can be modified to look for a trivial revision, or the smallest
  # non-trivial, instead of HEAD.
  new_revisions[repo] = repo.head_revision
  print(f'{repo}: {new_revisions[repo][:8]}')
  for dep, dep_revision in repo.get_deps().items():
    print(f'  {dep}: {dep_revision[:8]} -> {new_revisions[dep][:8]}')
    new_revisions[dep] = dep_revision

