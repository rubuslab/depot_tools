# Windows binary tool bootstrap

This directory has the 'magic' for the `depot_tools` windows binary update
mechanisms.

## Software bootstrapped
  * Python (https://www.python.org/)

## Mechanism

Any time a user runs `gclient` on windows, it will invoke the `depot_tools`
autoupdate script [depot_tools.bat](../../update_depot_tools.bat). This, in
turn, will run [win_tools.bat](./win_tools.bat), which does the bulk of the
work.

`win_tools.bat` will successively look to see if the local version of the binary
package is present, and if so, if it's the expected version. If either of those
cases is not true, it will download and unpack the respective binary.

Downloading is done with [get_file.js](./get_file.js), which is a windows script
host javascript utility to vaguely impersonate `wget`.

Through a comedy of history, each binary is stored and retrieved differently.

### Python

Python installs are sourced from gs://chrome-infra/python276_bin.zip .

The process to create them is sort-of-documented in the README of the python
zip file.
