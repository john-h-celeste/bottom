#! /bin/bash

set -ex

# install the user, group, server, stress daemon, and server restart cron job
# this script should be run using sudo

# create the user and group for the dashboard
useradd --comment 'Observability Dashboard' -m --system --shell '/bin/false' --user-group dashboard

DASHBOARDHOME=$(realpath ~dashboard)

# copy the service scripts and give them appropriate permissions
cp --target-directory "${DASHBOARDHOME}" server.sh restartserver.sh stress.sh
chmod 0500 "${DASHBOARDHOME}/server.sh"
chmod 0500 "${DASHBOARDHOME}/restartserver.sh" # this is run by root so it can use systemctl
chmod 0500 "${DASHBOARDHOME}/stress.sh"

chown dashboard:dashboard "${DASHBOARDHOME}/server.sh" "${DASHBOARDHOME}/stress.sh"

# add a service for the dashboard server
cat << EOF > /usr/lib/systemd/system/dashboard-server.service
[Unit]
Description=Linux Observability Dashboard Server Midterm Project Service

[Service]
Type=simple
ExecStart=${DASHBOARDHOME}/server.sh

[Install]
WantedBy=multi-user.target
EOF

systemctl enable dashboard-server.service

# add an entry to root crontab for the server restart process
cat << EOF >> /etc/crontab

*/5 * * * * ${DASHBOARDHOME}/restartserver.sh
EOF

systemctl restart cron.service

# add a service for the stress daemon
cat << EOF > /usr/lib/systemd/system/stress-tester.service
[Unit]
Description=Linux Observability Dashboard Server Midterm Project Stress Daemon Auxiliary Service

[Service]
Type=simple
ExecStart=${DASHBOARDHOME}/stress.sh

[Install]
WantedBy=multi-user.target
EOF

systemctl enable stress-tester.service

