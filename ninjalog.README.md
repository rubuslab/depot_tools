# Ninja build log collection

[TOC]

## What type of data are collected?

When chromium developers use autoninja for their build, autoninja uploads ninja
log.
In addition to ninja's build log, we collect following datas for further
analysis.

* OS (e.g. Win, Mac or Linux)
* number of cpu cores of building machine
* build targets (e.g. chrome, browser_tests)
* parallelism passed by -j flag
* following build configs
  * host\_os, host\_cpu
  * target\_os, target\_cpu
  * symbol\_level
  * use\_goma
  * is\_debug
  * is\_component\_build

Before uploading log, autoninja shows a message 10 times to users that we will
collect build log.

autoninja user can also opt in or out by following commands.

* `ninjalog_uploader_wrapper.py opt-in`
* `ninjalog_uploader_wrapper.py opt-out`


## Why ninja log is collected?


## How the collected logs are used?
