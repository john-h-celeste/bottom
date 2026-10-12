#! /bin/bash

set -e

# run by cron

if ! systemctl is-active --quiet dashboard-server.service; then
  systemctl restart dashboard-server.service
fi