#!/usr/bin/env python3
# Copyright 2023 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""This scripts copies DEPS package information from one source onto
destination.

If the destination doesn't have packages, the script errors out."""

import argparse
import ast
import sys


def _get_deps(deps_ast: ast.Module):
    """Searches for the deps dict in a DEPS file AST.

  Args:
    deps_ast: AST of the DEPS file.

  Raises:
    Exception: If the deps dict is not found.

  Returns:
    The deps dict.
  """
    for statement in deps_ast.body:
        if not isinstance(statement, ast.Assign):
            continue
        if len(statement.targets) != 1:
            continue
        target = statement.targets[0]
        if not isinstance(target, ast.Name):
            continue
        if target.id != 'deps':
            continue
        if not isinstance(statement.value, ast.Dict):
            continue
        deps = {}
        for key, value in zip(statement.value.keys, statement.value.values):
            if not isinstance(key, ast.Constant):
                continue
            deps[key.value] = value
        return deps
    raise Exception('no deps found')


def _get_gcs_object_list_ast(package_ast: ast.Dict) -> ast.List:
    """Searches for the objects list in a GCS package AST.

  Args:
    package_ast: AST of the GCS package.

  Raises:
    Exception: If the package is not a GCS package.

  Returns:
    AST of the objects list.
  """
    is_gcs = False
    result = None
    for key, value in zip(package_ast.keys, package_ast.values):
        if not isinstance(key, ast.Constant):
            continue
        if key.value == 'dep_type' and isinstance(
                value, ast.Constant) and value.value == 'gcs':
            is_gcs = True
        if key.value == 'objects' and isinstance(value, ast.List):
            result = value

    assert is_gcs, 'Not a GCS dependency!'
    assert result, 'No objects found!'
    return result


def _replace_ast(destination: str, dest_ast: ast.Module, source: str,
                 source_ast: ast.Module):
    """Replaces the content of dest_ast with the content of the
  same package in ast_source.

  Args:
    destination: Destination DEPS file content.
    dest_ast: AST of the destination DEPS file.
    source: Source DEPS file content.
    source_ast: AST of the source DEPS file.

  Returns:
    Destination DEPS file content with replaced content.
  """
    source_lines = source.splitlines()
    lines = destination.splitlines()
    # Copy all lines before the replaced AST.
    result = '\n'.join(lines[:dest_ast.lineno - 1]) + '\n'

    # Copy the line content before AST's value
    result += lines[dest_ast.lineno - 1][:dest_ast.col_offset]

    # Copy data from source AST.
    if source_ast.lineno == source_ast.end_lineno:
        # Starts and ends on the same line.
        result += source_lines[
            source_ast.lineno -
            1][source_ast.col_offset:source_ast.end_col_offset]
    else:
        # Multiline content. The first line and the last line of source AST
        # should be partially copied.

        # Partially copy the first line of source AST.
        result += source_lines[source_ast.lineno -
                               1][source_ast.col_offset:] + '\n'
        # Copy content in the middle.
        result += '\n'.join(
            source_lines[source_ast.lineno:source_ast.end_lineno - 1]) + '\n'
        # Partially copy the last line of source AST.
        result += source_lines[source_ast.end_lineno -
                               1][:source_ast.end_col_offset]

    # Copy the rest of the line after the package value.
    result += lines[dest_ast.end_lineno - 1][dest_ast.end_col_offset:] + '\n'

    # Copy the rest of the lines after the package value.
    result += '\n'.join(lines[dest_ast.end_lineno:])
    # Add trailing newline
    if destination.endswith('\n'):
        result += '\n'
    return result


def copy_packages(source, destination, packages):
    """Copies GCS packages from source to destination.

  Args:
    source: Source DEPS file content.
    destination: Destination DEPS file content.
    packages: List of GCS packages to copy. Only objects are copied.

  Returns:
    Destination DEPS file content with packages copied.
  """
    source_ast = ast.parse(source, mode='exec')
    deps = _get_deps(source_ast)
    for package in packages:
        if package not in deps:
            raise Exception('Package %s not found in source' % package)
        destination_ast = ast.parse(destination, mode='exec')
        dest_ast = _get_deps(destination_ast)
        if package not in dest_ast:
            raise Exception('Package %s not found in destination' % package)
        destination = _replace_ast(destination,
                                   _get_gcs_object_list_ast(dest_ast[package]),
                                   source,
                                   _get_gcs_object_list_ast(deps[package]))

    return destination


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',
                        required=True,
                        help='Source DEPS file where content will be copied '
                        'from')
    parser.add_argument('--package',
                        action='append',
                        required=True,
                        help='List of DEPS packages to update')
    parser.add_argument('--destination',
                        required=True,
                        help='Destination DEPS file, where content will be '
                        'saved')
    args = parser.parse_args()

    if not args.package or len(args.package) < 1:
        parser.error('No packages specified to roll, aborting...')

    with open(args.source) as f:
        source_content = f.read()

    with open(args.destination) as f:
        destination_content = f.read()

    new_content = copy_packages(source_content, destination_content,
                                args.package)

    with open(args.destination, 'w') as f:
        f.write(new_content)

    print('Run:')
    print('  Destination DEPS file updated. You still need to create and '
          'upload a change.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
