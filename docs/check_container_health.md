# check_container_health.py

Nagios/Icinga plugin for monitoring Docker container health, state, restart counts, CPU usage, memory usage, and process counts.

Current version: **1.0.1**

## Features

`check_container_health.py` can monitor all Docker containers on a host or a single selected container.

The plugin supports:

- Automatic Docker runtime detection
- Monitoring all Docker containers on a host
- Monitoring a single container by name or container ID
- Shell-style include and exclude filtering
- Expected-container monitoring
- Container state monitoring
- Docker HEALTHCHECK monitoring
- OOM-killed container detection
- Docker lifetime restart-count monitoring
- CPU usage monitoring
- Memory usage monitoring
- PID count collection
- Configurable WARNING and CRITICAL thresholds
- Nagios-compatible performance data
- Verbose and debug output
- Nagios-compatible exit codes
- Command timeout handling
- Docker daemon and command failure detection
- No third-party Python modules required

Version 1.0.1 supports Docker.

Podman is not yet supported.

## Requirements

- Python 3
- Docker CLI
- Docker Engine
- Permission to communicate with the Docker daemon
- Nagios, Icinga, NRPE, or another Nagios-compatible monitoring system

No third-party Python modules are required.

The plugin has been tested with Python:

- 3.9
- 3.11
- 3.13

## Installation

Copy the plugin to the standard Nagios plugin directory.

On RHEL-compatible systems this is commonly:

```text
/usr/lib64/nagios/plugins
```

Example:

```bash
sudo cp check_container_health.py /usr/lib64/nagios/plugins/
sudo chmod 755 /usr/lib64/nagios/plugins/check_container_health.py
```

Verify the installed version:

```bash
/usr/lib64/nagios/plugins/check_container_health.py --version
```

Example:

```text
check_container_health.py 1.0.1
```

## Docker access

The account running the plugin must be able to communicate with the Docker daemon.

Test this with:

```bash
docker info
```

and:

```bash
docker ps
```

The plugin does not require write access to containers and does not create, start, stop, restart, pause, or remove containers.

It performs read-only Docker queries.

Depending on the host configuration, Docker access may require membership in the Docker group or a narrowly scoped privilege configuration.

Docker daemon access should be granted carefully because access to the Docker socket is security-sensitive.

## Basic usage

Check all containers:

```bash
./check_container_health.py
```

Example:

```text
CONTAINERS OK: 5 containers, 5 running, no problems | containers=5 running=5 stopped=0 paused=0 restarting=0 unhealthy=0 oom_killed=0 missing=0 restarts=0
```

## Single-container monitoring

Use `--container` to monitor exactly one container.

Example:

```bash
./check_container_health.py \
  --container kof-grafana
```

Example output:

```text
CONTAINERS OK: kof-grafana running, health=none, restarts=0 | containers=1 running=1 stopped=0 paused=0 restarting=0 unhealthy=0 oom_killed=0 missing=0 restarts=0
```

A container can be selected by:

- Exact container name
- Full container ID
- Unique container ID prefix

Example:

```bash
./check_container_health.py \
  --container 07e4f91ddf6b
```

If the requested container does not exist:

```text
CONTAINERS CRITICAL: container 'example' not found
```

The plugin returns exit code `2`.

If an ID prefix matches more than one container, the plugin returns UNKNOWN.

`--container` cannot be combined with:

- `--include`
- `--exclude`
- `--expect`

## Include filtering

Only monitor containers whose names match a shell-style pattern:

```bash
./check_container_health.py \
  --include 'kof-*'
```

`--include` may be specified multiple times:

```bash
./check_container_health.py \
  --include 'kof-*' \
  --include 'atom-*'
```

## Exclude filtering

Exclude containers whose names match a shell-style pattern:

```bash
./check_container_health.py \
  --exclude 'test-*'
```

Multiple exclusions are supported:

```bash
./check_container_health.py \
  --exclude 'test-*' \
  --exclude 'temporary-*'
```

`--exclude` takes precedence over `--include`.

Example:

```bash
./check_container_health.py \
  --include 'atom-*' \
  --exclude '*fluent-bit'
```

## Expected containers

Use `--expect` when a container must exist.

Example:

```bash
./check_container_health.py \
  --expect kof-grafana \
  --expect kof-nginx_be
```

If all expected containers exist, monitoring continues normally.

If an expected container is missing:

```text
CONTAINERS CRITICAL: expected container 'kof-grafana' is missing
```

The performance data also reports the number of missing expected containers:

```text
missing=1
```

`--expect` does not filter the monitored container list.

It only verifies that the named containers exist.

## Container states

The plugin evaluates Docker container states.

Default state mapping:

| Docker state | Nagios state |
|---|---|
| `running` | OK |
| `paused` | WARNING |
| `restarting` | WARNING |
| `created` | WARNING |
| `exited` | CRITICAL |
| `dead` | CRITICAL |
| unexpected/unknown state | CRITICAL |

For an exited container, the Docker exit code is included in the problem output.

Example:

```text
CONTAINERS CRITICAL: application: exited (1)
```

## Docker HEALTHCHECK monitoring

Docker HEALTHCHECK state monitoring is enabled by default.

Supported states include:

| Health state | Nagios state |
|---|---|
| `healthy` | OK |
| no HEALTHCHECK | OK |
| `starting` | WARNING |
| `unhealthy` | CRITICAL |

A container does not need to define a Docker HEALTHCHECK.

Containers without one are reported internally as:

```text
health=none
```

This is considered OK.

Disable health-state evaluation with:

```bash
./check_container_health.py \
  --no-health
```

For example, an otherwise running container with Docker health state `unhealthy` is ignored when `--no-health` is used.

## OOM-killed containers

The plugin checks Docker's `OOMKilled` state.

If Docker reports:

```text
OOMKilled=true
```

the container is considered CRITICAL.

Example:

```text
CONTAINERS CRITICAL: worker: OOM-killed
```

This is checked even if the container is currently running again.

This helps detect containers that were terminated because of memory pressure and subsequently restarted.

## Problem-count thresholds

By default, a container state or health problem results in CRITICAL.

Optional aggregate thresholds can be configured:

```bash
./check_container_health.py \
  --warning 1 \
  --critical 3
```

This means:

- Fewer than 1 problematic container: OK
- 1-2 problematic containers: WARNING
- 3 or more problematic containers: CRITICAL

The thresholds apply to selected containers with state or health problems.

## Restart monitoring

Restart-count monitoring is optional.

Enable it with:

```bash
./check_container_health.py \
  --check-restarts
```

Default restart thresholds are:

```text
WARNING:  3
CRITICAL: 5
```

Example:

```bash
./check_container_health.py \
  --check-restarts \
  --restart-warning 3 \
  --restart-critical 5
```

A container with three restarts returns WARNING.

A container with five or more restarts returns CRITICAL.

### Important restart-count behavior

The plugin uses Docker's:

```text
RestartCount
```

value.

This is a Docker lifetime restart counter for the current container object.

It is **not** an interval-based restart counter.

For example:

```bash
--restart-warning 3
```

means the container's Docker `RestartCount` has reached at least 3.

Version 1.0.1 does not implement a `--since` time window for restart monitoring.

## Resource monitoring

Resource monitoring is optional because collecting Docker statistics is more expensive than basic container-state inspection.

Enable it with:

```bash
./check_container_health.py \
  --check-resources
```

The plugin collects:

- CPU usage
- Memory usage
- Memory percentage
- PID count

Example:

```text
CONTAINERS OK: kof-grafana running, health=none, restarts=0, CPU 0.05%, memory 2.22%
```

Performance data is also generated.

Example:

```text
'kof-grafana_cpu'=0.05%
'kof-grafana_memory'=2.22%
'kof-grafana_memory_bytes'=178887065B
'kof-grafana_pids'=16
```

## CPU thresholds

CPU thresholds require `--check-resources`.

Example:

```bash
./check_container_health.py \
  --container kof-grafana \
  --check-resources \
  --cpu-warning 80 \
  --cpu-critical 95
```

A CPU value at or above the WARNING threshold returns WARNING.

A CPU value at or above the CRITICAL threshold returns CRITICAL.

Example:

```text
CONTAINERS CRITICAL: application: CPU 97.20% >= 95%
```

### CPU usage above 100%

Docker CPU percentages can exceed 100% on multi-core systems.

For example:

```text
237.40%
```

is a valid Docker CPU value.

The plugin therefore allows CPU thresholds greater than 100.

Example:

```bash
./check_container_health.py \
  --check-resources \
  --cpu-warning 200 \
  --cpu-critical 300
```

## Memory thresholds

Memory thresholds also require `--check-resources`.

Example:

```bash
./check_container_health.py \
  --container kof-grafana \
  --check-resources \
  --memory-warning 80 \
  --memory-critical 90
```

Memory thresholds are percentages.

Valid values are greater than 0 and at most 100.

Example problem:

```text
CONTAINERS WARNING: kof-grafana: memory 85.00% >= 80%
```

## Docker memory limits

Docker statistics normally provide memory usage in a form similar to:

```text
170.6MiB / 7.5GiB
```

The plugin also checks the container's Docker `HostConfig.Memory` value.

If:

```text
HostConfig.Memory = 0
```

the container has no explicit Docker memory limit.

In verbose output the plugin indicates this:

```text
memory: 170.6 MiB / 7.50 GiB, 2.22%, no explicit container limit
```

In this situation, the limit reported by Docker statistics may represent the memory available through the host/cgroup environment rather than an explicitly configured per-container memory limit.

## Combined resource monitoring

CPU and memory thresholds can be used together:

```bash
./check_container_health.py \
  --container kof-grafana \
  --check-resources \
  --cpu-warning 80 \
  --cpu-critical 95 \
  --memory-warning 80 \
  --memory-critical 90
```

The highest resulting Nagios severity wins.

For example, if CPU is WARNING and memory is CRITICAL, the final state is CRITICAL.

## Resource monitoring for all containers

Resource data can be collected for every selected container:

```bash
./check_container_health.py \
  --check-resources
```

Resource and restart monitoring can also be combined:

```bash
./check_container_health.py \
  --check-restarts \
  --check-resources
```

This provides container state, restart information, CPU, memory, PID counts, and performance data in a single Nagios check.

## Performance data

Basic performance data includes:

```text
containers
running
stopped
paused
restarting
unhealthy
oom_killed
missing
restarts
```

Example:

```text
containers=5 running=5 stopped=0 paused=0 restarting=0 unhealthy=0 oom_killed=0 missing=0 restarts=0
```

With `--check-resources`, additional per-container metrics are generated:

```text
'<container>_cpu'
'<container>_memory'
'<container>_memory_bytes'
'<container>_pids'
```

Example:

```text
'kof-grafana_cpu'=0.05%
'kof-grafana_memory'=2.22%
'kof-grafana_memory_bytes'=178887065B
'kof-grafana_pids'=16
```

If thresholds are configured, they are included in the Nagios performance data.

Example:

```text
'kof-grafana_cpu'=50.00%;80;95
'kof-grafana_memory'=75.00%;80;90;0;100
```

## Verbose output

Use `-v` for detailed container information:

```bash
./check_container_health.py \
  --container kof-grafana \
  --check-resources \
  -v
```

Example:

```text
Runtime: docker
Containers discovered: 5
Containers after filtering: 1
Excluded containers: 0
kof-grafana:
  id: 07e4f91ddf6b
  image: example/grafana:latest
  state: running
  health: none
  restarts: 0
  restart policy: always
  oom killed: False
  cpu: 0.05%
  memory: 170.6 MiB / 7.50 GiB, 2.22%, no explicit container limit
  pids: 16
```

Use `-vv` for additional debug information:

```bash
./check_container_health.py \
  --container kof-grafana \
  --check-restarts \
  -vv
```

Debug output includes:

- Container selector
- Include patterns
- Exclude patterns
- Expected containers
- Problem-count thresholds
- Restart monitoring state
- Restart thresholds
- Resource monitoring state
- CPU thresholds
- Memory thresholds
- Command timeout
- Maximum output details

## Maximum problem details

Nagios plugin output should remain reasonably short.

Use:

```bash
--max-details N
```

to control how many individual problem descriptions are included.

Default:

```text
5
```

Example:

```bash
./check_container_health.py \
  --max-details 10
```

Additional problems are summarized as:

```text
+3 more
```

## Command timeout

The default Docker command timeout is:

```text
30 seconds
```

Change it with:

```bash
./check_container_health.py \
  --timeout 60
```

or:

```bash
./check_container_health.py \
  -t 60
```

A Docker command timeout results in UNKNOWN.

## Runtime selection

Runtime autodetection is the default:

```bash
./check_container_health.py \
  --runtime auto
```

Explicit Docker selection:

```bash
./check_container_health.py \
  --runtime docker
```

Version 1.0.1 does not support Podman.

Attempting:

```bash
./check_container_health.py \
  --runtime podman
```

returns:

```text
CONTAINERS UNKNOWN: Podman support is not available in version 1.0.1
```

with exit code `3`.

## Exit codes

The plugin uses standard Nagios exit codes:

| Exit code | State |
|---:|---|
| 0 | OK |
| 1 | WARNING |
| 2 | CRITICAL |
| 3 | UNKNOWN |

UNKNOWN is used for conditions such as:

- Docker executable not found
- Docker daemon unavailable
- Docker command failure
- Docker command timeout
- Invalid Docker inspect JSON
- Invalid plugin arguments
- Ambiguous container ID prefix
- Unsupported runtime

## Help

Display command-line help:

```bash
./check_container_health.py --help
```

Display the version:

```bash
./check_container_health.py --version
```

or:

```bash
./check_container_health.py -V
```

## NRPE integration

Install the plugin:

```bash
sudo cp check_container_health.py /usr/lib64/nagios/plugins/
sudo chmod 755 /usr/lib64/nagios/plugins/check_container_health.py
```

Before configuring NRPE, verify that the NRPE account can access Docker.

For example:

```bash
sudo -u nrpe docker info
```

and:

```bash
sudo -u nrpe docker ps
```

If these commands fail, the plugin will also be unable to query Docker.

### Basic NRPE command

Example:

```text
command[check_container_health]=/usr/lib64/nagios/plugins/check_container_health.py
```

### Monitor container health and restarts

```text
command[check_container_health]=/usr/lib64/nagios/plugins/check_container_health.py --check-restarts
```

### Monitor all container resources

```text
command[check_container_resources]=/usr/lib64/nagios/plugins/check_container_health.py --check-resources
```

### Monitor a specific container

```text
command[check_container_grafana]=/usr/lib64/nagios/plugins/check_container_health.py --container kof-grafana --check-restarts --check-resources --cpu-warning 80 --cpu-critical 95 --memory-warning 80 --memory-critical 90
```

After changing the NRPE configuration, validate the NRPE configuration according to the local installation and restart or reload NRPE as appropriate.

Then test remotely from the Nagios server.

Example:

```bash
/usr/lib64/nagios/plugins/check_nrpe \
  -H <host> \
  -c check_container_health
```

## Nagios command example

Example Nagios command definition:

```text
define command {
    command_name    check_container_health
    command_line    $USER1$/check_nrpe -H $HOSTADDRESS$ -c check_container_health
}
```

Example service:

```text
define service {
    use                     generic-service
    host_name               docker-host
    service_description     Docker Container Health
    check_command           check_container_health
}
```

## Example configurations

### Basic host monitoring

```bash
./check_container_health.py
```

### Health and restart monitoring

```bash
./check_container_health.py \
  --check-restarts
```

### Full resource monitoring

```bash
./check_container_health.py \
  --check-restarts \
  --check-resources \
  --cpu-warning 80 \
  --cpu-critical 95 \
  --memory-warning 80 \
  --memory-critical 90
```

### Single critical application

```bash
./check_container_health.py \
  --container important-application \
  --check-restarts \
  --check-resources \
  --cpu-warning 80 \
  --cpu-critical 95 \
  --memory-warning 80 \
  --memory-critical 90
```

### Require specific containers

```bash
./check_container_health.py \
  --expect grafana \
  --expect nginx \
  --expect database
```

### Monitor only a group of containers

```bash
./check_container_health.py \
  --include 'production-*'
```

### Monitor a group but ignore one container

```bash
./check_container_health.py \
  --include 'production-*' \
  --exclude 'production-maintenance'
```

## Testing

The plugin includes a hardware-independent automated test suite.

The tests cover:

- Argument validation
- Docker runtime detection
- Docker command execution
- Docker command failures
- Docker command timeouts
- Docker inspect JSON parsing
- Containers without HEALTHCHECK
- Healthy containers
- Unhealthy containers
- OOM-killed containers
- Running state
- Created state
- Paused state
- Restarting state
- Exited state
- Dead state
- Unexpected states
- Restart-count thresholds
- Docker statistics parsing
- CPU percentage parsing
- CPU usage above 100%
- Memory unit parsing
- Memory percentage thresholds
- Resource statistics merging
- Include filtering
- Exclude filtering
- Include/exclude precedence
- Exact container-name selection
- Full container-ID selection
- Unique container-ID prefix selection
- Ambiguous ID handling
- Expected-container checks
- Nagios problem-count thresholds
- Performance data
- Performance-data threshold formatting
- Main OK paths
- Main WARNING paths
- Main CRITICAL paths
- Main UNKNOWN paths

The current test suite contains:

```text
109 tests
```

Example:

```bash
python3 -m unittest ./test_check_container_health.py -v
```

Validated result for version 1.0.1:

```text
Ran 109 tests

OK
```

The repository CI runs the test suite with:

- Python 3.9
- Python 3.11
- Python 3.13

## Safety

The plugin is designed as a read-only monitoring tool.

It does not intentionally:

- Create containers
- Start containers
- Stop containers
- Restart containers
- Pause or unpause containers
- Remove containers
- Modify images
- Modify container configuration

Container state information is obtained from Docker inspection commands.

Resource information is obtained from Docker statistics.

## Limitations

Version 1.0.1 has the following known limitations:

- Docker is the only supported container runtime.
- Podman is not yet supported.
- Restart monitoring uses Docker's lifetime `RestartCount`.
- Restart monitoring does not currently support a time window.
- Resource monitoring uses Docker's current `stats --no-stream` snapshot.
- CPU and memory measurements therefore represent a point-in-time observation.
- Memory percentages are based on the limit reported by Docker statistics.
- A Docker-reported memory limit does not necessarily mean an explicit per-container memory limit was configured.
- Containers without Docker HEALTHCHECK cannot be application-health checked by this plugin; their health state is reported as `none`.

## License

MIT
