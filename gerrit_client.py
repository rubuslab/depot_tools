#!/usr/bin/python
# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Simple client for the Gerrit REST API.

Example usage:
  ./gerrit_client.py --host [host_name] --path [rest path] -b ""
"""

import argparse
import json
import logging
import sys
import time
import urlparse

from gerrit_util import CreateHttpConn, ReadHttpJsonResponse

def gerrit_call(host, path, reqtype, body, attempts=3):
  retry_delay_seconds = 1
  attempt = 1
  while True:
    try:
      return ReadHttpJsonResponse(CreateHttpConn(host, path, reqtype=reqtype,
                                                 body=body), ignore_404=False)
    except Exception as e:
      if attempt >= attempts:
        raise
      logging.exception('Failed to perform gerrit operation: %s', e)

    # Retry from previous loop.
    logging.error('Sleeping %d seconds before retry (%d/%d)...',
                  retry_delay_seconds, attempt, attempts)
    time.sleep(retry_delay_seconds)
    retry_delay_seconds *= 2
    attempt += 1

def main(arguments):
  parser = create_argparser()
  args = parser.parse_args(arguments)

  host = urlparse.urlparse(args.host).netloc

  path = str(args.path)
  reqtype = str(args.request_type).upper()
  assert reqtype in ['PUT', 'GET', 'POST']
  body_json = {}
  if args.body:
    body_json = json.loads(str(args.body))
  if args.body_file:
    logging.warning("--body-file will override --body.")
    with open(args.body_file, 'r') as body_json_file:
      body_json = json.loads(body_json_file.read())

  if not args.dry_run:
    result = gerrit_call(host, path, reqtype, body_json, args.dry_run)
  with open(args.json_file, 'w') as json_file:
    json_file.write(json.dumps(result))
  return 0


def create_argparser():
  parser = argparse.ArgumentParser()
  parser.add_argument('--host', required=True, help='Url of host.')
  parser.add_argument('-p', '--path', required=True, help='RestAPI path')
  parser.add_argument('--request_type', required=True, help='request_type')
  parser.add_argument('-b', '--body', required=False, help='request body')
  parser.add_argument('--body_file', required=False,
                      help='request body json file')
  parser.add_argument('--json_file', required=True,
                      help='output json filepath')
  parser.add_argument('--dry_run', type=bool, default=False,
                      help='is dry run mode')
  parser.add_argument('-a', '--attempts', type=int, default=1,
                      help='The number of attempts to make (with exponential '
                           'backoff) before failing. If several requests are '
                           'to be made, applies per each request separately.')
  # TODO(dimu): Does it need an additional authenciation flag?
  # To specify .netrc/.gitcookies to use, etc?
  return parser


if __name__ == '__main__':
  logging.basicConfig()
  logging.getLogger().setLevel(logging.INFO)
  sys.exit(main(sys.argv[1:]))