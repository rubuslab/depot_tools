import requests

from google.cloud import storage

import html


_HOST = 'https://codereview.chromium.org/'
_BUCKET_NAME = 'chromium-review-lemur-test'

_ISSUE_PAGE = 'Issue'
_PATCH_SET_PAGE = 'PatchSet'
_PATCH_PAGE = 'Patch'


session = requests.Session()
storage_client = storage.Client()


def process_page(path, page_type, private):
  response = session.get(
      posixpath.join(_HOST, path), headers=_get_auth_headers())

  # Forward transient errors to the client so tasks can be retried.
  if response.status_code >= 500 or response.status_code == 429:
    return response.text, response.status_code

  if response.status_code != 200:
    content = response.text
  elif page_type == _ISSUE_PAGE:
    content = html.process_issue(response.text)
  elif page_type == _PATCH_SET_PAGE:
    content = html.process_patch_set(response.text)
  elif page_type == _PATCH_PAGE:
    content = html.process_patch(response.text)

  if page_type == _ISSUE_PAGE:
    if not path.endswith('/'):
      path += '/'
    path += 'index.html'

  bucket = storage_client.get_bucket(_BUCKET_NAME)
  blob = bucket.blob(path)
  blob.upload_from_string(content)
  blob.metadata = {
    'Rietveld-Private': private,
    'Status-Code': response.status_code,
  }
  blob.content_type = response.headers['content-type']
  blob.patch()

  return ''


def _get_auth_headers():
  TOKEN_URL = ('http://metadata.google.internal/computeMetadata/v1'
               '/instance/service-accounts/default/token')
  TOKEN_HEADERS = {'Metadata-Flavor': 'Google'}

  response = session.get(TOKEN_URL, headers=TOKEN_HEADERS)
  response.raise_for_status()

  # Extract the access token from the response.
  access_token = response.json()['access_token']

  return {'Authorization': f'Bearer {access_token}'}
