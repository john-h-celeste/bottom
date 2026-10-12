requirements:
1. deploy to gcp
2. stress-ng bash script
3. service to start stress-ng
4. use named pipes
5. create a user and group for the api server
6. custom api server to monitor metrics
7. custom dashboard to monitor remotely
    1. essential metrics
    2. visualize realtime and hostorical data with with charts and graphs
    3. dashboard automatically collects data
    4. thresholds and notification by dashboard
8. limit access by ip address
9. restart api server on failure (cron) (systemctl?)
10. multiple servers, one dashboard
11. everyone uses github

deliverables:
1. report
    1. cover - name, github, date, section, names
    2. introduction
    3. design
    4. experimental results and analysis
    5. problems
    6. what was learned
2. code - well commented and organized - stress, api server, cron job, dashboard
3. video
    1. display normal operation
    2. autorestart
    3. stress
4. live test