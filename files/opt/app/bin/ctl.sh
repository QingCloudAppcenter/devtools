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
EC_CHECK_PROTO_ERR=130

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
  local retCode=0
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

getServices() {
  if [ "$1" = "-a" ]; then
    echo $SERVICES
  else
    echo $SERVICES | xargs -n1 | awk -F/ '$2=="true"'
  fi
}

_init() {
  mkdir -p /data/appctl/logs
  chown -R syslog.adm /data/appctl/logs

  rm -rf /data/lost+found

  local svc; for svc in $(getServices -a); do
    systemctl unmask -q ${svc%%/*}
  done
}

checkSvc() {
  systemctl is-active -q $1
}

checkEndpoint() {
  local host=$MY_IP proto=${1%:*} port=${1#*:}
  if [ "$proto" = "tcp" ]; then
    nc -w5 $host $port
  elif [ "$proto" = "udp" ]; then
    nc -u -q5 -w5 $host $port
  elif [ "$proto" = "http" ]; then
    local code="$(curl -s -o /dev/null -w "%{http_code}" $host:$port)"
    [[ "$code" =~ ^(200|302|401|403|404)$ ]]
  else
    return $EC_CHECK_PROTO_ERR
  fi
}

checkHttpStatuses() {
  local port; for port in $svcPorts; do checkHttpStatus $MY_IP $port; done
}

_check() {
  local svc; for svc in $(getServices); do
    checkSvc ${svc%%/*}
    local endpoints=$(echo $svc | awk -F/ '{print $3}')
    local endpoint; for endpoint in ${endpoints//,/ }; do
      checkEndpoint $endpoint
    done
  done
}

isInitialized() {
  local svcs="$(getServices -a)"
  [ "$(systemctl is-enabled -q ${svcs%%/*})" = "disabled" ]
}

_start() {
  isInitialized || execute init
  local svc; for svc in $(getServices); do
    systemctl start ${svc%%/*}
  done
}

_stop() {
  local svc; for svc in $(getServices -a | xargs -n1 | tac); do
    systemctl stop ${svc%%/*}
  done
}

_restart() {
  execute stop && execute start
}

_revive() {
  execute check || execute restart
}

_update() {
  if isInitialized; then execute restart; fi # only update when unmasked
}

. /opt/app/bin/role.sh

execute $command $args
