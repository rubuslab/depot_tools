#!/usr/bin/env python
# Copyright 2018 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""This is script to upload ninja_log from googler."""

import argparse
import cStringIO
import gzip
import json
import logging
import multiprocessing
import os
import platform
import socket
import sys

from third_party import httplib2

def IsGoogler(server):
    """Check whether this script run inside corp network."""
    h = httplib2.Http()
    _, content = h.request('https://'+server+'/should-upload', 'GET')
    return content == 'Success'

def GetMetadata(args):
    """Get metadata for uploaded ninjalog."""

    # TODO(tikuta): Support build_configs from args.gn.

    build_dir = os.path.dirname(args.ninjalog)
    metadata = {
        'platform': platform.system(),
        'cwd': build_dir,
        'hostname': socket.gethostname(),
        'cpu_core': multiprocessing.cpu_count(),
        'cmdline': args.cmdline,
    }

    return metadata

def GetNinjalog(cmdline):
    """GetNinjalog returns the path to ninjalog from cmdline.

    >>> GetNinjalog(['ninja'])
    './.ninja_log'
    >>> GetNinjalog(['ninja', '-C', 'out/Release'])
    'out/Release/.ninja_log'
    >>> GetNinjalog(['ninja', '-Cout/Release'])
    'out/Release/.ninja_log'
    >>> GetNinjalog(['ninja', '-C'])
    './.ninja_log'
    """
    # ninjalog is in current working directory by default.
    ninjalog_dir = '.'

    for i, cmd in enumerate(cmdline):
        if cmd == '-C' and i + 1 < len(cmdline):
            ninjalog_dir = cmdline[i+1]
            break

        if cmd.startswith('-C') and len(cmd) > len('-C'):
            ninjalog_dir = cmd[len('-C'):]
            break

    return os.path.join(ninjalog_dir, '.ninja_log')

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--server',
                        default='chromium-build-stats.appspot.com',
                        help='server to upload ninjalog file.')
    parser.add_argument('--ninjalog', help='ninjalog file to upload.')
    parser.add_argument('--verbose', action='store_true',
                        help='Enable verbose logging.')
    parser.add_argument('--cmdline', required=True, nargs=argparse.REMAINDER,
                        help='command line args passed to ninja.')

    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.INFO)
    else:
        # Disable logging.
        logging.disable(logging.CRITICAL)

    if not IsGoogler(args.server):
        return 0


    ninjalog = args.ninjalog or GetNinjalog(args.cmdline)
    if not os.path.isfile(ninjalog):
        logging.warn("ninjalog is not found in %s", ninjalog)
        return 1

    output = cStringIO.StringIO()

    with open(ninjalog) as f:
        with gzip.GzipFile(fileobj=output, mode='wb') as g:
            g.write(f.read())
            g.write('# end of ninja log\n')

            metadata = GetMetadata(args)
            logging.info('send metadata: %s', metadata)
            g.write(json.dumps(metadata))

    h = httplib2.Http()
    resp_headers, content = h.request(
        'https://'+args.server+'/upload_ninja_log/', 'POST',
        body=output.getvalue(), headers={'Content-Encoding': 'gzip'})

    if resp_headers.status != 200:
        logging.warn("unexpected status code for response: %s",
                     resp_headers.status)
        return 1

    logging.info('response header: %s', resp_headers)
    logging.info('response content: %s', content)
    return 0

if __name__ == '__main__':
    sys.exit(main())
