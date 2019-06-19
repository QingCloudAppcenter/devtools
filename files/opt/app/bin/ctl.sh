#!/usr/bin/env bash

# Default hook functions named starting with _, e.g. _init(), _start(), etc.
# Specific roles can override the default hooks like:
#   start() {
#     _start
#     ...
#   }
#
# Specific hooks will be executed if exist, otherwise the default ones.

set -eo pipefail

. /opt/app/bin/version.env
. /opt/app/bin/.env

# Error codes
EC_DEFAULT=1          # default
EC_RETRY_FAILED=2

command=$1
args="${@:2}"

log() {
  logger -t appctl --id=$$ [cmd=$command] "$@"
}

retry() {
  local tried=0
  local maxAttempts=$1
  local interval=$2
  local stopCode=$3
  local cmd="${@:4}"
  local retCode=$EC_RETRY_FAILED
  while [ $tried -lt $maxAttempts ]; do
    $cmd && return 0 || {
      retCode=$?
      if [ "$retCode" = "$stopCode" ]; then
        log "'$cmd' returned with stop code $stopCode. Stopping ..." && return $retCode
      fi
    }
    sleep $interval
    tried=$((tried+1))
  done

  log "'$cmd' still returned errors after $tried attempts. Stopping ..." && return $retCode
}

execute() {
  local cmd=$1
  [ "$(type -t $cmd)" = "function" ] || cmd=_$cmd
  $cmd ${@:2}
}

reverseSvcNames() {
  echo $svcNames | tr ' ' '\n' | tac | tr '\n' ' '
}

svcsctl() {
  local svcName; for svcName in $svcNames; do systemctl $@ $svcName; done
}

_init() {
  mkdir -p /data/appctl/logs
  chown -R syslog.adm /data/appctl/logs

  rm -rf /data/lost+found

  svcsctl unmask -q
}

checkSvcs() {
  svcsctl is-active -q
}

checkHttpStatus() {
  local host=${1:-$MY_IP} port=${2:-80}
  local code="$(curl -s -o /dev/null -w "%{http_code}" $host:$port)"
  [[ "$code" =~ ^(200|302|401|403|404)$ ]] || {
    log "HTTP status check failed to $host:$port: code=$code."
    return 5
  }
}

checkHttpStatuses() {
  local port; for port in $svcPorts; do checkHttpStatus $MY_IP $port; done
}

_check() {
  checkSvcs
  checkHttpStatuses
}

_start() {
  svcsctl is-enabled -q || execute init
  svcsctl start
  retry ${svcStartTimeout:-120} 1 0 execute check
}

_stop() {
  svcNames="$(reverseSvcNames)" svcsctl stop
}

_restart() {
  execute stop && execute start
}

_revive() {
  execute check || execute restart
}

_update() {
  if [ "$(systemctl is-enabled $MY_ROLE)" = "disabled" ]; then execute restart; fi # only update when unmasked
}

. /opt/app/bin/role.sh

execute $command $args
