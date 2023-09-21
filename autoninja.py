#!/usr/bin/env python3
# Copyright (c) 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""
This script (intended to be invoked by autoninja or autoninja.bat) detects
whether a build is accelerated using a service like goma. If so, it runs with a
large -j value, and otherwise it chooses a small one. This auto-adjustment
makes using remote build acceleration simpler and safer, and avoids errors that
can cause slow goma builds or swap-storms on unaccelerated builds.

autoninja tries to detect relevant build settings such as use_remoteexec, and
it does handle import statements, but it can't handle conditional setting of
build settings.
"""

from contextlib import ExitStack
import multiprocessing
import os
import platform
import re
import shlex
import subprocess
import sys
from typing import List, Iterator
import uuid

import reclient_helper

if sys.platform in ['darwin', 'linux']:
    import resource

# Enable during debugging to print more verbose log messages.
DEBUG = os.environ.get('AUTONINJA_DEBUG', '0') == '1'

SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))

# See [1] and [2] for the painful details of this next section, which handles
# escaping command lines so that they can be copied and pasted into a cmd
# window.
#
# [1] https://learn.microsoft.com/en-us/archive/blogs/twistylittlepassagesallalike/everyone-quotes-command-line-arguments-the-wrong-way
# [2] https://web.archive.org/web/20150815000000*/https://www.microsoft.com/resources/documentation/windows/xp/all/proddocs/en-us/set.mspx
UNSAFE_FOR_CMD = set('^<>&|()%')
ALL_META_CHARS = UNSAFE_FOR_CMD.union(set('"'))


def quote_for_cmd(arg):
    # First, escape the arg so that CommandLineToArgvW will parse it properly.
    if arg == '' or ' ' in arg or '"' in arg:
        quote_re = re.compile(r'(\\*)"')
        arg = '"%s"' % (quote_re.sub(lambda mo: 2 * mo.group(1) + '\\"', arg))

    # Then check to see if the arg contains any metacharacters other than
    # double quotes; if it does, quote everything (including the double
    # quotes) for safety.
    if any(a in UNSAFE_FOR_CMD for a in arg):
        arg = ''.join('^' + a if a in ALL_META_CHARS else a for a in arg)
    return arg


def print_cmd(cmd):
    shell_quoter = shlex.quote
    if sys.platform.startswith('win'):
        shell_quoter = quote_for_cmd
    print(*[shell_quoter(arg) for arg in cmd], file=sys.stderr)


def gn_lines(output_dir: str, path: str) -> Iterator[str]:
    """
    Generator function that returns args.gn lines one at a time, following
    import directives as needed.
    """
    import_re = re.compile(r'\s*import\("(.*)"\)')
    with open(path, encoding='utf-8') as f:
        for line in f:
            match = import_re.match(line)
            if match:
                raw_import_path = match.groups()[0]
                if raw_import_path[:2] == "//":
                    import_path = os.path.normpath(
                        os.path.join(output_dir, '..', '..',
                                     raw_import_path[2:]))
                else:
                    import_path = os.path.normpath(
                        os.path.join(os.path.dirname(path), raw_import_path))
                for import_line in gn_lines(output_dir, import_path):
                    yield import_line
            else:
                yield line


def main(args: List[str]) -> int:
    # The -t tools are incompatible with -j
    t_specified = False
    j_specified = False
    offline = False
    output_dir = '.'
    summarize_build = os.environ.get('NINJA_SUMMARIZE_BUILD', '0') == '1'
    # On Windows the autoninja.bat script passes along the arguments enclosed
    # in double quotes. This prevents multiple levels of parsing of the
    # special '^' characters needed when compiling a single file but means
    # that this script gets called with a single argument containing all of
    # the actual arguments, separated by spaces. When this case is detected we
    # need to do argument splitting ourselves. This means that arguments
    # containing actual spaces are not supported by autoninja, but that is not
    # a real limitation.
    if (sys.platform.startswith('win') and len(args) == 2
            and args[1].count(' ') > 0):
        args = args[:1] + args[1].split()

    if DEBUG:
        print("autoninja: args = {}".format(args), file=sys.stderr)

    # Ninja uses getopt_long, which allow to intermix non-option arguments.
    # To leave non supported parameters untouched, we do not use getopt.
    for index, arg in enumerate(args[1:]):
        if arg.startswith('-j'):
            j_specified = True
        if arg.startswith('-t'):
            t_specified = True
        if arg == '-C':
            # + 1 to get the next argument and +1 because we trimmed off
            # args[0]
            output_dir = args[index + 2]
        elif arg.startswith('-C'):
            # Support -Cout/Default
            output_dir = arg[2:]
        elif arg in ('-o', '--offline'):
            offline = True
        elif arg == '-h':
            print('autoninja: Use -o/--offline to temporary disable goma.',
                  file=sys.stderr)
            print(file=sys.stderr)

    use_goma = False
    use_remoteexec = False
    use_rbe = False
    use_siso = False

    # Attempt to auto-detect remote build acceleration. We support gn-based
    # builds, where we look for args.gn in the build tree, and cmake-based
    # builds where we look for rules.ninja.
    if os.path.exists(os.path.join(output_dir, 'args.gn')):
        for line in gn_lines(output_dir, os.path.join(output_dir, 'args.gn')):
            # use_goma, use_remoteexec, or use_rbe will activate build
            # acceleration.
            #
            # This test can match multi-argument lines. Examples of this
            # are: is_debug=false use_goma=true is_official_build=false
            # use_goma=false# use_goma=true This comment is ignored
            #
            # Anything after a comment is not consider a valid argument.
            line_without_comment = line.split('#')[0]
            if re.search(r'(^|\s)(use_goma)\s*=\s*true($|\s)',
                         line_without_comment):
                use_goma = True
                continue
            if re.search(r'(^|\s)(use_remoteexec)\s*=\s*true($|\s)',
                         line_without_comment):
                use_remoteexec = True
                continue
            if re.search(r'(^|\s)(use_rbe)\s*=\s*true($|\s)',
                         line_without_comment):
                use_rbe = True
                continue
            if re.search(r'(^|\s)(use_siso)\s*=\s*true($|\s)',
                         line_without_comment):
                use_siso = True
                continue
    else:
        for relative_path in [
                '',  # GN keeps them in the root of output_dir
                'CMakeFiles'
        ]:
            path = os.path.join(output_dir, relative_path, 'rules.ninja')
            if os.path.exists(path):
                with open(path, encoding='utf-8') as file_handle:
                    for line in file_handle:
                        if re.match(r'^\s*command\s*=\s*\S+gomacc', line):
                            use_goma = True
                            break

    # Exit early when we hit an unsupported configuration.
    if use_siso and use_goma:
        print('Siso does not support use_goma=true. Please check the Chromium '
              'developer docs how to migrate to reclient and then '
              'change your GN args in %s to use_remoteexec=true instead.' %
              output_dir,
              file=sys.stderr)
        return 1

    # Makes the following conditions easier to read. :)
    use_ninja = not use_siso

    # Siso generates a .ninja_log file, too, so the mere existence of a
    # .ninja_log file doesn't imply that a ninja build was done. However
    # if there is a .ninja_log but no .siso_deps then that implies a
    # ninja build.
    has_ninja_marker = os.path.exists(os.path.join(output_dir, '.ninja_log'))
    last_build_used_siso = os.path.exists(os.path.join(output_dir,
                                                       '.siso_deps'))
    last_build_used_ninja = has_ninja_marker and not last_build_used_siso
    if use_siso and last_build_used_ninja:
        print('Run "gn clean %s" before switching from Ninja to Siso in that '
              'output directory.' % output_dir,
              file=sys.stderr)
        return 1
    if use_ninja and last_build_used_siso:
        print('Run "gn clean %s" before switching from Siso to Ninja in that '
              'output directory.' % output_dir,
              file=sys.stderr)
        return 1

    # If GOMA_DISABLED is set to "true", "t", "yes", "y", or "1"
    # (case-insensitive) then gomacc will use the local compiler instead of
    # doing a goma compile. This is convenient if you want to briefly disable
    # goma. It avoids having to rebuild the world when transitioning between
    # goma/non-goma builds. However, it is not as fast as doing a "normal"
    # non-goma build because an extra process is created for each compile step.
    # Checking this environment variable ensures that autoninja uses an
    # appropriate -j value in this situation.
    goma_disabled_env = os.environ.get('GOMA_DISABLED', '0').lower()
    if offline or goma_disabled_env in ['true', 't', 'yes', 'y', '1']:
        use_goma = False

    if use_goma:
        gomacc_file = 'gomacc.exe' if sys.platform.startswith(
            'win') else 'gomacc'
        goma_dir = os.environ.get('GOMA_DIR',
                                  os.path.join(SCRIPT_DIR, '.cipd_bin'))
        gomacc_path = os.path.join(goma_dir, gomacc_file)
        # Don't invoke gomacc if it doesn't exist.
        if os.path.exists(gomacc_path):
            # Check to make sure that goma is running. If not, don't start the
            # build.
            status = subprocess.call([gomacc_path, 'port'],
                                     stdout=subprocess.PIPE,
                                     stderr=subprocess.PIPE,
                                     shell=False)
            if status == 1:
                print(
                    'Goma is not running. Use "goma_ctl ensure_start" to '
                    'start it.',
                    file=sys.stderr)
                return 1

    # A large build (with or without goma) tends to hog all system resources.
    # Depending on the operating system, we might have mechanisms available
    # to run at a lower priority, which improves this situation.
    if os.environ.get('NINJA_BUILD_IN_BACKGROUND', '0') == '1':
        if sys.platform in ['darwin', 'linux']:
            # nice-level 10 is usually considered a good default for background
            # tasks. The niceness is inherited by child processes, so we can
            # just set it here for us and it'll apply to the build tool we
            # spawn later.
            os.nice(10)

    if offline:
        # Tell goma or reclient to do local compiles.
        os.environ['RBE_remote_disabled'] = "1"
        os.environ['GOMA_DISABLED'] = "1"
        if use_ninja:
            # Ninja doesn't understand -o/--offline, so we remove them from the
            # args.
            args = [arg for arg in args if arg not in ('-o', '--offline')]

    if use_ninja:
        # reclient's racing feature is not compatible with Siso, so we only
        # enable it for Ninja.
        os.environ.setdefault("RBE_exec_strategy", "racing")

    # Set a unique build ID if not already set by the user.
    os.environ.setdefault("AUTONINJA_BUILD_ID", str(uuid.uuid4()))

    # Delight the user with a more detailed UI if they enabled
    # NINJA_SUMMARIZE_BUILD and haven't yet set their own NINJA_STATUS string.
    # In particular this makes it possible to see how quickly process creation
    # is happening - often a critical clue on Windows. The trailing space is
    # intentional.
    if summarize_build:
        os.environ.setdefault("NINJA_STATUS",
                              "[%r processes, %f/%t @ %o/s : %es ] ")

    # On macOS and most Linux distributions, the default limit of open file
    # descriptors is too low (256 and 1024, respectively).
    # This causes a large j value to result in 'Too many open files' errors.
    # Raise the limit, if we can.
    if sys.platform in ['darwin', 'linux']:
        # Increase the number of allowed open file descriptors to the maximum.
        fileno_limit, hard_limit = resource.getrlimit(resource.RLIMIT_NOFILE)
        if fileno_limit < hard_limit:
            try:
                resource.setrlimit(resource.RLIMIT_NOFILE,
                                   (hard_limit, hard_limit))
            except (ValueError, resource.error) as e:
                if DEBUG:
                    print("autoninja: Failed to raise ulimit: {}".format(e),
                          file=sys.stderr)

    # Call siso.py / ninja.py so that it can find the build tool binary
    # installed by DEPS or one in PATH.
    if use_siso:
        # Siso requires additionally specifying the "ninja" subcommand.
        build_tool = [os.path.join(SCRIPT_DIR, 'siso.py'), "ninja"]
        if use_remoteexec or use_rbe:
            # Siso doesn't need to do authentication when we use reproxy, so
            # disable it.
            build_tool += ['-project=', '-reapi_instance=']
    else:
        build_tool = [os.path.join(SCRIPT_DIR, 'ninja.py')]

    num_cores = multiprocessing.cpu_count()
    # Siso automatically computes the correct number of jobs, so we only need
    # to do this for Ninja.
    if use_ninja and not j_specified and not t_specified:
        if not offline and (use_goma or use_remoteexec or use_rbe):
            args.append('-j')
            default_core_multiplier = 80
            if platform.machine() in ('x86_64', 'AMD64'):
                # Assume simultaneous multithreading and therefore half as many
                # cores as logical processors.
                num_cores //= 2

            core_multiplier = int(
                os.environ.get('NINJA_CORE_MULTIPLIER',
                               default_core_multiplier))
            j_value = num_cores * core_multiplier

            core_limit = int(os.environ.get('NINJA_CORE_LIMIT', j_value))
            j_value = min(j_value, core_limit)

            # On Windows, a -j higher than 1000 doesn't improve build times.
            # On macOS, ninja is limited to at most FD_SETSIZE (1024) open file
            # descriptors.
            if sys.platform in ['darwin', 'win32']:
                j_value = min(j_value, 1000)

            # Use a j value that reliably works with the open file descriptors
            # limit.
            if sys.platform in ['darwin', 'linux']:
                j_value = min(j_value, int(fileno_limit * 0.8))

            args.append('%d' % j_value)
        else:
            j_value = num_cores
            # Ninja defaults to |num_cores + 2|
            j_value += int(os.environ.get('NINJA_CORE_ADDITION', '2'))
            args.append('-j')
            args.append('%d' % j_value)

    args = [sys.executable] + build_tool + args[1:]

    if summarize_build:
        # Enable statistics collection in Ninja. Siso doesn't need this flag.
        if use_ninja:
            args += ['-d', 'stats']
        # Print the command-line to reassure the user that the right
        # settings are being used.
        print_cmd(args)

    try:
        with ExitStack() as stack:
            if use_remoteexec or use_rbe:
                toolname = 'ninja_reclient' if use_ninja else 'autosiso'
                ret_code = stack.enter_context(
                    reclient_helper.build_context(output_dir, toolname))
                if ret_code:
                    return ret_code
            subprocess.run(args, check=True)
    except subprocess.CalledProcessError as e:
        if DEBUG:
            print("autoninja: Build failed with return code: {}".format(
                e.returncode))
        return e.returncode
    except KeyboardInterrupt:
        if DEBUG:
            print(
                "autoninja: Caught keyboard interrupt during build, exiting...")
        return 1
    finally:
        # Collect ninjalog from Googlers.
        try:
            ninjalog_uploader_wrapper_args = [
                sys.executable,
                os.path.join(SCRIPT_DIR, "ninjalog_uploader_wrapper.py"),
                "--cmdline"
            ] + args
            if DEBUG:
                print_cmd(ninjalog_uploader_wrapper_args)
            subprocess.run(ninjalog_uploader_wrapper_args, check=True)
        except subprocess.CalledProcessError as e:
            if DEBUG:
                print(
                    "autoninja: ninjalog_uploader_wrapper.py failed: {}".format(
                        e),
                    file=sys.stderr)

    if summarize_build:
        try:
            post_build_ninja_summary_args = [
                sys.executable,
                os.path.join(SCRIPT_DIR, "post_build_ninja_summary.py")
            ] + args
            if DEBUG:
                print_cmd(post_build_ninja_summary_args)
            subprocess.run(post_build_ninja_summary_args, check=True)
        except subprocess.CalledProcessError as e:
            if DEBUG:
                print(
                    "autoninja: post_build_ninja_summary.py failed: {}".format(
                        e),
                    file=sys.stderr)


if __name__ == '__main__':
    try:
        sys.exit(main(sys.argv))
    except KeyboardInterrupt:
        if DEBUG:
            print(
                "autoninja: Caught keyboard interrupt in main, exiting now...")
        sys.exit(1)
