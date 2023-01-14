# Apt Exporter

## Quick Start

```bash
DOCKER_BUILDKIT=1 docker build -t apt-exporter .
docker run -dit --name apt-exporter -v /var/lib/dpkg/status:/var/lib/dpkg/status apt-exporter
```

## Metrics

```bash
# HELP apt_package APT Package Information
# TYPE apt_package gauge
apt_package{description="add and remove users and groups",job="apt-exporter",package="adduser",priority="important",section="admin",status="install ok installed",version="3.118ubuntu5"} 1.0
# HELP apt_package APT Package Information
# TYPE apt_package gauge
apt_package{description="Processor microcode firmware for AMD CPUs",job="apt-exporter",package="amd64-microcode",priority="standard",section="non-free/admin",status="install ok installed",version="3.20191218.1ubuntu2"} 1.0
# HELP apt_package APT Package Information
# TYPE apt_package gauge
apt_package{description="user-space parser utility for AppArmor",job="apt-exporter",package="apparmor",priority="optional",section="admin",status="install ok installed",version="3.0.4-2ubuntu2.1"} 1.0
# HELP apt_package APT Package Information
# TYPE apt_package gauge
apt_package{description="automatically generate crash reports for debugging",job="apt-exporter",package="apport",priority="optional",section="utils",status="install ok installed",version="2.20.11-0ubuntu82.3"} 1.0
# HELP apt_package APT Package Information
# TYPE apt_package gauge
apt_package{description="symptom scripts for apport",job="apt-exporter",package="apport-symptoms",priority="optional",section="utils",status="install ok installed",version="0.24"} 1.0
# HELP apt_package APT Package Information
# TYPE apt_package gauge
apt_package{description="commandline package manager",job="apt-exporter",package="apt",priority="important",section="admin",status="install ok installed",version="2.4.8"} 1.0
# HELP apt_package APT Package Information
# TYPE apt_package gauge
apt_package{description="transitional package for https support",job="apt-exporter",package="apt-transport-https",priority="optional",section="oldlibs",status="install ok installed",version="2.4.8"} 1.0
...
```
