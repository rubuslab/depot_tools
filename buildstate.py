"""
This script (Windows only) checks to see what build commands are currently
running by printing the command lines of any processes that are the children of
ninja.exe processes.

The idea is that if the build is serialized (not many build steps running) then
you can run this to see what it is serialized on.
"""

from __future__ import print_function

import subprocess

cmd = 'wmic process get Caption,ParentProcessId,ProcessId,CommandLine'
lines = subprocess.check_output(cmd, universal_newlines=True).splitlines()

kCaptionOff = 0
kCommandLineOff = lines[0].find('CommandLine')
kParentPidOff = lines[0].find('ParentProcessId')
kPidOff = lines[0].find(' ProcessId') + 1

parents = []

processes = []

print('Tracking the children of these commands:')
for line in lines[1:]:
  # Ignore blank lines
  if not line.strip():
    continue
  command = line[:kCommandLineOff].strip()
  command_line = line[kCommandLineOff:kParentPidOff].strip()
  parent_pid = int(line[kParentPidOff:kPidOff].strip())
  pid = int(line[kPidOff:].strip())
  processes.append((command, command_line, parent_pid, pid))
  if command == 'ninja.exe':
    print('%d, %d: %s' % (parent_pid, pid, command_line))
    parents.append(pid)
print()

print('%d processes found, tracking %d parent(s).' %
      (len(processes), len(parents)))
print()

count = 0
for process in processes:
  command, command_line, parent_pid, pid = process
  if parent_pid in parents:
    if not command_line:
      command_line = command
    print('%5d: %s' % (pid, command_line[:160]))
    count += 1
print('Found %d children' % count)
