#!/usr/bin/env bash
. demo_repo.sh

run git map-branches -v
run git checkout origin/master
praw vi foo \&\& git add -A \&\& git commit -m 'foo'
silent echo 'foo' >foo
silent git add -A
silent git commit -m 'foo'
run git new-branch independent_cl
run git map-branches -v
run git new-branch --upstream subfeature nested_cl
run git map-branches -v
run git rebase @{upstream}
run git map-branches -v
callout 3
run git checkout cool_feature 2>&1
run git new-branch --upstream_current cl_depends_on_cool_feature
run git map-branches -v
