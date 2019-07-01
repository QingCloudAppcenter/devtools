#!/usr/bin/env bash

set -eo pipefail

app=${1?specify app name}
baseDir=/root/workspace/apps
appDir=$baseDir/$app
plays="
$baseDir/base/pre-make.yml
$appDir/ansible/make.yml
$baseDir/base/post-make.yml
"

for play in $plays; do target=${2-dev} ansible-playbook -i $appDir/ansible/hosts $play; done
