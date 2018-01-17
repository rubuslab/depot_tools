# Copyright (c) 2018 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""This script is designed to be automatically run after each ninja build in
order to summarize the build's performance. Making build performance information
more visible should make it easier to notice anomalies and opportunities. To use
this script just create a ninja.bat file containing the three lines below and
put it in a directory which is earlier in your path than depot_tools. The path
to depot_tools will need to be fixed up on the second line:

@echo off
FOR /f "usebackq tokens=*" %%a in (`python.bat ^
        c:\src\depot_tools\autoninja.py "%*"`) do echo %%a & %%a
@if errorlevel 1 goto buildfailure
python %~dp0post_build_ninja_summary.py %*
:buildfailure

You can also call this script directly using ninja's syntax to specify the
output directory of interest:

> python post_build_ninja_summary.py -C out/Default

Typical output currently looks like this:

>ninja -C out\debug_component base
ninja.exe -C out\debug_component base -j 960 -l 48  -d keeprsp
ninja: Entering directory `out\debug_component'
[1 processes, 1/1 @ 0.3/s : 3.092s ] Regenerating ninja files
[1 processes, 23/23 @ 0.9/s : 26.280s ] LINK(DLL) base.dll base.dll.lib
    Longest build steps:
           0.9 weighted s to build obj/base/base_jumbo_17.obj (5.0 s CPU time)
           1.0 weighted s to build obj/base/base_jumbo_31.obj (13.1 s CPU time)
           1.2 weighted s to build obj/base/base_jumbo_4.obj (14.7 s CPU time)
           1.3 weighted s to build obj/base/base_jumbo_32.obj (15.0 s CPU time)
           1.6 weighted s to build obj/base/base_jumbo_26.obj (17.1 s CPU time)
           1.7 weighted s to build base.dll, base.dll.lib (1.7 s CPU time)
           1.7 weighted s to build obj/base/base_jumbo_11.obj (15.9 s CPU time)
           1.9 weighted s to build obj/base/base_jumbo_12.obj (18.5 s CPU time)
           3.6 weighted s to build obj/base/base_jumbo_34.obj (20.1 s CPU time)
           4.3 weighted s to build obj/base/base_jumbo_33.obj (22.3 s CPU time)
    Time by build-step type:
           0.1 s weighted time to generate 1 .c files (0.1 s CPU time)
           0.1 s weighted time to generate 1 .stamp files (0.1 s CPU time)
           0.2 s weighted time to generate 1 .h files (0.2 s CPU time)
           1.7 s weighted time to generate 1 PEFile files (1.7 s CPU time)
          24.3 s weighted time to generate 19 .obj files (233.4 s CPU time)
    26.3 s weighted time (235.5 s CPU time, 9.0x parallelism)
    23 build steps completed, average of 0.88/s

If no gn clean has been done then results will be for the last non-NULL
invocation of ninja. Ideas for future statistics, and implementations are
appreciated.

The "weighted" time is the elapsed time of each build step divided by the number
of tasks that were running in parallel. This makes it an excellent approximation
of how "important" a slow step was. A link that is entirely or mostly serialized
will have a weighted time that is the same or similar to its elapsed time. A
compile that runs in parallel with 999 other compiles will have a weighted time
that is tiny."""

import os
import sys


# The number of long build times to report:
long_count = 10
# The number of long times by extension to report
long_ext_count = 5


class Target:
    """Represents a single line read for a .ninja_log file."""
    def __init__(self, start, end):
        self.start = int(start)
        self.end = int(end)
        self.targets = []
        # Weighted_duration takes the elapsed time of the task and divides it
        # by how many other tasks were running at the same time.
        # weighted_duration should always be the same or shorter than duration.
        self.weighted_duration = 0.0
    def Duration(self):
        return self.end - self.start
    def SetWeightedDuration(self, weighted_duration):
        self.weighted_duration = weighted_duration
    def WeightedDuration(self):
        # Allow for modest floating-point errors
        epsilon = 0.002
        if (self.weighted_duration > self.Duration() + epsilon):
          print '%s > %s?' % (self.weighted_duration, self.Duration())
        assert(self.weighted_duration <= self.Duration() + epsilon)
        return self.weighted_duration
    def DescribeTargets(self):
        if len(self.targets) == 1:
          return self.targets[0]
        # Some build steps generate dozens of outputs - handle them sanely.
        elif len(self.targets) > 3:
          return '(%d items) ' % len(self.targets) + (
                 ', '.join(self.targets[:2]) + ', ...')
        else:
          return ', '.join(self.targets)


# Copied with some modifications from ninjatracing
def read_targets(log, show_all):
    """Reads all targets from .ninja_log file |log_file|, sorted by duration"""
    header = log.readline()
    assert header == '# ninja log v5\n', \
           'unrecognized ninja log version %r' % header
    targets = {}
    last_end_seen = 0
    for line in log:
        parts = line.strip().split('\t')
        if len(parts) != 5:
          # If ninja.exe is rudely halted then the .ninja_log file may be
          # corrupt. Silently continue.
          continue
        start, end, _, name, cmdhash = parts # Ignore restat.
        if not show_all and int(end) < last_end_seen:
            # An earlier time stamp means that this step is the first in a new
            # build, possibly an incremental build. Throw away the previous
            # data so that this new build will be displayed independently.
            targets = {}
        last_end_seen = int(end)
        targets.setdefault(cmdhash, Target(start, end)).targets.append(name)
    return targets.values()


def GetExtension(target):
  for output in target.targets:
    if output.count('.mojom') > 0:
      extension = 'mojo'
      break
    if output.endswith('type_mappings'):
      extension = 'type_mappings'
      break
    extension = os.path.splitext(output)[1]
    if len(extension) == 0:
      extension = '(no extension found)'
    # AHEM____.TTF fails this check.
    assert(extension == extension.lower() or extension == '.TTF')
    if extension in ['.pdb', '.dll', '.exe']:
      extension = 'PEFile (linking)'
      # Make sure that .dll and .exe are grouped together and that the
      # .dll.lib files don't cause these to be listed as libraries
      break
  return extension


def summarize_entries(entries):
    # Create a list that is in order by time stamp and has entries for the
    # beginning and ending of each build step (one time stamp may have multiple
    # entries due to multiple steps starting/stopping at exactly the same time).
    # Iterate through this list, keeping track of which tasks are running at all
    # times. At each time step 'charge' each task which is running for an amount
    # of time equal to the elapsed time divided by the number of tasks which
    # were running. The weighted duration can then be reported along with
    # elapsed time.
    task_start_stop_times = []

    # Sum up the total time consumed, and the start/stop times.
    earliest = -1
    latest = 0
    total_cpu_time = 0
    for target in entries:
      if earliest < 0 or target.start < earliest:
        earliest = target.start
      if target.end > latest:
        latest = target.end
      total_cpu_time += target.Duration()
      task_start_stop_times.append((target.start, 'start', target))
      task_start_stop_times.append((target.end, 'stop', target))
    length = latest - earliest
    weighted_total = 0.0

    task_start_stop_times.sort()
    # Now we have all task start/stop times sorted by when they happen. If a
    # task starts and stops on the same time stamp then the start will come
    # first because of the alphabet, which is important for making this work
    # correctly.
    # Track the tasks which are currently running.
    running_tasks = {}
    # Record the time we have processed up to so we know how to calculate time
    # deltas.
    last_time = task_start_stop_times[0][0]
    # Track the accumulated weighted time so that it can efficiently be added
    # to individual tasks.
    last_weighted_time = 0.0
    # Scan all start/stop events.
    for event in task_start_stop_times:
      time, action_name, target = event
      # Accumulate weighted time up to now.
      num_running = len(running_tasks)
      if num_running > 0:
        # Update the total weighted time up to this moment.
        last_weighted_time += (time - last_time) / float(num_running)
      if action_name == 'start':
        # Record the total weighted task time when this task starts.
        running_tasks[target] = last_weighted_time
      if action_name == 'stop':
        # Record the change in the total weighted task time while this task ran.
        weighted_duration = last_weighted_time - running_tasks[target]
        target.SetWeightedDuration(weighted_duration)
        weighted_total += weighted_duration
        del running_tasks[target]
      last_time = time
    assert(len(running_tasks) == 0)

    # Warn if the sum of weighted times is off by more than half a second.
    if abs(length - weighted_total) > 500:
      print 'Discrepancy!!! Length = %.3f, weighted total = %.3f' % (
            length / 1000.0, weighted_total / 1000.0)

    print '    Longest build steps:'
    entries.sort(key=lambda x: x.WeightedDuration())
    for target in entries[-long_count:]:
      print '      %8.1f weighted s to build %s (%.1f s CPU time)' % (
            target.WeightedDuration() / 1000.0,
            target.DescribeTargets(), target.Duration() / 1000.0)

    # Sum up the time by file extension/type of the output file
    count_by_extensions = {}
    time_by_extensions = {}
    weighted_time_by_extensions = {}
    for target in entries:
      extension = GetExtension(target)
      time_by_extensions[extension] = time_by_extensions.get(extension, 0) + target.Duration()
      weighted_time_by_extensions[extension] = weighted_time_by_extensions.get(extension, 0) + target.WeightedDuration()
      count_by_extensions[extension] = count_by_extensions.get(extension, 0) + 1

    print '    Time by build-step type:'
    # Copy to a list with extension name and total time swapped.
    weighted_time_by_extensions_sorted = map(lambda x: (x[1], x[0]), weighted_time_by_extensions.items())
    weighted_time_by_extensions_sorted.sort()
    for extension in weighted_time_by_extensions_sorted[-long_ext_count:]:
        print '      %8.1f s weighted time to generate %d %s files (%1.1f s CPU time)' % (extension[0] / 1000.0,
              count_by_extensions[extension[1]], extension[1], time_by_extensions[extension[1]] / 1000.0)

    print '    %.1f s weighted time (%.1f s CPU time, %1.1fx parallelism)' % (
          length / 1000.0, total_cpu_time / 1000.0,
          total_cpu_time * 1.0 / length)
    print '    %d build steps completed, average of %1.2f/s' % (
          len(entries), len(entries) / (length / 1000.0))


def main(argv):
    log_file = '.ninja_log'
    for pid, arg in enumerate(argv):
        if arg == '-C':
          log_file = os.path.join(argv[pid+1], log_file)

    try:
      with open(log_file, 'r') as log:
        entries = read_targets(log, False)
        summarize_entries(entries)
    except IOError:
      print 'No log file found, no build summary created.'


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
