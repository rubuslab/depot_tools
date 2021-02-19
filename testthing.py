import owners_client
import gerrit_util

client = owners_client.GerritClient(
  'chromium-review.googlesource.com',
  'chromium/tools/depot_tools',
  'refs/heads/master')

print(client.ListOwners('presubmit_support.py'))
