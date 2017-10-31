#!/bin/bash
# This alias allows invocations of `python2` to work as expected under msys bash.
# In particular, it detects if stdout+stdin are both attached to a pseudo-tty,
# and if so, invokes python2 in interactive mode. If this is not the case, or
# the user passes any arguments, python2 will be invoked unmodified.
python2() {
  if [[ $# > 0 ]]; then
    python2.exe "$@"
  else
    readlink /proc/$$/fd/0 | grep pty > /dev/null
    TTY0=$?
    readlink /proc/$$/fd/1 | grep pty > /dev/null
    TTY1=$?
    if [ $TTY0 == 0 ] && [ $TTY1 == 0 ]; then
      python2.exe -i
    else
      python2.exe
    fi
  fi
}
