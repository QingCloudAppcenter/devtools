#!/usr/bin/env bash

set -eo pipefail

app=${1?specify app name}
plays="
/root/workspace/apps/base/pre-make.yml
/root/workspace/apps/$app/ansible/make.yml
/root/workspace/apps/base/post-make.yml
"

for play in $plays; do target=${2-dev} ansible-playbook -i hosts $play; done
