#!/usr/bin/env vpython3
# Copyright (c) 2020 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Smoke tests for gclient.py.

Shell out 'gclient' and run gcs tests.
"""

import logging
import os
import sys
import unittest

from unittest import mock
import gclient_smoketest_base
import subprocess2

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class GClientSmokeGcs(gclient_smoketest_base.GClientSmokeBase):

    def setUp(self):
        super(GClientSmokeGcs, self).setUp()
        self.enabled = self.FAKE_REPOS.set_up_git()
        if not self.enabled:
            self.skipTest('git fake repos not available')
        self.env['PATH'] = (os.path.join(ROOT_DIR, 'testing_support') +
                            os.pathsep + self.env['PATH'])

    def testSyncGcs(self):
        self.gclient(['config', self.git_base + 'repo_22', '--name', 'src'])
        self.gclient(['sync'])

        tree = self.mangle_git_tree(('repo_22@1', 'src'))
        tree.update({
            'src/another_gcs_dep/hash':
            '355957fc33440edf4bee2e2fd4ef4671f73f1085\n',
            'src/another_gcs_dep/llvmfile.tar.gz':
            'tarfile',
            'src/another_gcs_dep/extracted_dir/extracted_file':
            'extracted text',
            'src/gcs_dep/deadbeef':
            'tarfile',
            'src/gcs_dep/hash':
            'f49cf6381e322b147053b74e4500af8533ac1e4c\n',
            'src/gcs_dep/extracted_dir/extracted_file':
            'extracted text',
        })
        self.assertTree(tree)

    def testConvertGitToGcs(self):
        self.gclient(['config', self.git_base + 'repo_22', '--name', 'src'])

        # repo_13@1 has src/repo12 as a git dependency.
        self.gclient([
            'sync', '-v', '-v', '-v', '--revision',
            self.githash('repo_13', 1)
        ])

        tree = self.mangle_git_tree(('repo_13@1', 'src'),
                                    ('repo_12@1', 'src/repo12'))
        self.assertTree(tree)

        # repo_13@3 has src/repo12 as a cipd dependency.
        self.gclient([
            'sync', '-v', '-v', '-v', '--revision',
            self.githash('repo_13', 3), '--delete_unversioned_trees'
        ])

        tree = self.mangle_git_tree(('repo_13@3', 'src'))
        tree.update({
            '_cipd':
            '\n'.join([
                '$ParanoidMode CheckPresence',
                '$OverrideInstallMode copy',
                '',
                '@Subdir src/repo12',
                'foo 1.3',
                '',
                '',
            ]),
            'src/repo12/_cipd':
            'foo 1.3',
        })
        self.assertTree(tree)

    def _testConvertGcsToGit(self):
        self.gclient(['config', self.git_base + 'repo_13', '--name', 'src'])

        # repo_13@3 has src/repo12 as a cipd dependency.
        self.gclient([
            'sync', '-v', '-v', '-v', '--revision',
            self.githash('repo_13', 3), '--delete_unversioned_trees'
        ])

        tree = self.mangle_git_tree(('repo_13@3', 'src'))
        tree.update({
            '_cipd':
            '\n'.join([
                '$ParanoidMode CheckPresence',
                '$OverrideInstallMode copy',
                '',
                '@Subdir src/repo12',
                'foo 1.3',
                '',
                '',
            ]),
            'src/repo12/_cipd':
            'foo 1.3',
        })
        self.assertTree(tree)

        # repo_13@1 has src/repo12 as a git dependency.
        self.gclient([
            'sync', '-v', '-v', '-v', '--revision',
            self.githash('repo_13', 1)
        ])

        tree = self.mangle_git_tree(('repo_13@1', 'src'),
                                    ('repo_12@1', 'src/repo12'))
        tree.update({
            '_cipd':
            '\n'.join([
                '$ParanoidMode CheckPresence',
                '$OverrideInstallMode copy',
                '',
                '@Subdir src/repo12',
                'foo 1.3',
                '',
                '',
            ]),
            'src/repo12/_cipd':
            'foo 1.3',
        })
        self.assertTree(tree)

    def _testRevInfo(self):
        self.gclient(['config', self.git_base + 'repo_18', '--name', 'src'])
        self.gclient(['sync'])
        results = self.gclient(['revinfo'])
        out = ('src: %(base)srepo_18\n'
               'src/cipd_dep:package0: %(instance_url1)s\n'
               'src/cipd_dep:package0/${platform}: %(instance_url2)s\n'
               'src/cipd_dep:package1/another: %(instance_url3)s\n' % {
                   'base':
                   self.git_base,
                   'instance_url1':
                   CHROME_INFRA_URL + '/package0@package0-fake-tag:1.0',
                   'instance_url2':
                   CHROME_INFRA_URL +
                   '/package0/${platform}@package0/${platform}-fake-tag:1.0',
                   'instance_url3':
                   CHROME_INFRA_URL +
                   '/package1/another@package1/another-fake-tag:1.0',
               })
        self.check((out, '', 0), results)

    def _testRevInfoActual(self):
        self.gclient(['config', self.git_base + 'repo_18', '--name', 'src'])
        self.gclient(['sync'])
        results = self.gclient(['revinfo', '--actual'])
        out = (
            'src: %(base)srepo_18@%(hash1)s\n'
            'src/cipd_dep:package0: %(instance_url1)s\n'
            'src/cipd_dep:package0/${platform}: %(instance_url2)s\n'
            'src/cipd_dep:package1/another: %(instance_url3)s\n' % {
                'base':
                self.git_base,
                'hash1':
                self.githash('repo_18', 1),
                'instance_url1':
                # The below 'fake-*' and 'platform-expanded-*' ID's are from:
                # ../testing_support/fake_cipd.py. 'fake-resolved' represents
                # the package being found in the batch resolution mechanism.
                CHROME_INFRA_URL + '/p/package0/+/package0-fake-resolved-id',
                'instance_url2':
                CHROME_INFRA_URL + '/p/package0/platform-expanded-test-only' +
                '/+/package0/${platform}-fake-instance-id',
                'instance_url3':
                CHROME_INFRA_URL + '/p/package1/another' +
                '/+/package1/another-fake-resolved-id',
            })
        self.check((out, '', 0), results)


if __name__ == '__main__':
    if '-v' in sys.argv:
        logging.basicConfig(level=logging.DEBUG)
    unittest.main()
