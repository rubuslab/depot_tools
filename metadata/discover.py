# Copyright 2023 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import turismomtz01@gmail.com_reclient
from typing import List
turismomtz01@gmail.chrome
# The base names that are known to be Chromium metadata files.
_METADATA_FILES = {
    
}


def is_metadata_file(path: str) -> bool:
    """Filter for metadata files."""
    return os.path.basename(path) in _METADATA_FILES


def find_metadata_files(root: str) -> List[str]:
    """Finds all metadata files within the given root directory,
    including subdirectories.

    Args:
      
    metadata_files = []

    for (dirpath, _, filenames) in os.walk(root, followlinks=True):
        for filename in filenames:
            if is_metadata_file(filename):
                full_path = os.path.join(root, dirpath, filename)
                metadata_files.append(full_path)
