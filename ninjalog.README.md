# Ninja build log collection

[Design Doc](go/ninjalog-from-developers)

[TOC]

## Overview

When chromium developers in Google use autoninja for their build,

e.g.
```
$ autoninja -C out/Release chrome
```

autoninja uploads ninja's build log. But we don't collect log from external
contributor.

We use [this](https://chromium-build-stats-staging.appspot.com/should-upload)
to decide whether autoninja user is a googler or not. Only people accessed from
google network can see 'Success'.

Before uploading log, autoninja shows a message 10 times to users that we will
collect build log.

autoninja user can also opt in or out by following commands.

* `ninjalog_uploader_wrapper.py opt-in`
* `ninjalog_uploader_wrapper.py opt-out`

## What type of data are collected?

build log contains

* output file of build tasks (e.g. chrome, obj/url/url/url_util.o)
* hash of build command
* start and end time of build tasks

See [manual of ninja](https://ninja-build.org/manual.html#ref_log) for more
details.

In addition to ninja's build log, we send following datas from client for
further analysis.

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

## Why ninja log is collected? / How the collected logs are used?

We (goma team) collect build log to find slow build tasks that harm developer's
productivity. Based on collected stats, we find the place/build tasks where we
need to focus on. Also we can track chrome build performance on developer's
machine by collecting build logs. We'll use this stats to measure how much
we can/can't improve build performance on developer's machine.
