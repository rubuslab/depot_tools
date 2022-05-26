#!/bin/bash
#
# citc WORKSPACE
#
#  Create a Cog workspace and clone a chromium repository.
#
#   For example:
#   $ clone_chromium my-chromium-workspace
#

function citc_workspace() {
  local workspace=${1:-""}

  git citc create "${workspace}" "sso://chromium/infra/infra" --path_in_workspace=infra
  #git citc create "${workspace}"
  
  cd "$(p4 g4d "${workspace}")"

  fetch --force -p="sso" infra
}

function main() {
  local workspace_name=${1:-""}
  if [[ -z "${workspace_name}" ]]; then
    gbash::print_usage
    gbash::quiet_die "Missing workspace name"
  fi
  citc_workspace "$workspace_name"
}

main "$@"

# "infra/luci":
#     "{chromium_git}/infra/luci/luci-py@13f9dc21ec7e1236e343396de5bec354fd6f4cb2",
