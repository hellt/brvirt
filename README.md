# About brvirt
`brvirt` displays bridges and enclosed interfaces along with corresponding
KVM Virtual Machines names and virsh domain ids.

It answers one simple question:
**How to determine which virtual interface belongs to which virtual
machine and what bridge it is in?"**

![brvirt_demo](https://img-fotki.yandex.ru/get/197852/21639405.11d/0_8b9d6_3d8bd18_orig.gif)
# Requirements
The script is compatible with `python2.7` and `python3+`.

- `brvirt` uses `virsh` tool to list VM properties and virtual network interfaces. To install `virsh` use:
```
 # on Debian-based distros:
sudo apt-get install libvirt-bin

 # on RHEL based:
sudo yum install libvirt
```

- Apart from virsh, the script relies on [tabulate](https://bitbucket.org/astanin/python-tabulate) python package to render console tables:
```shell
TABULATE_INSTALL=lib-only pip install tabulate
```

# Usage
As simple as `python brvirt.py`
will produce the following output which combines `brctl` and `virsh domiflist` commands output:
```
(brvirt) [root@leo ~]# python brvirt.py
+----------+---------------+-----------+-------------+--------------------+
| Bridge   | Interface     | VM name   | Domain ID   | Int. MAC address   |
|----------+---------------+-----------+-------------+--------------------|
| br0      | eno1          |           |             | 28:80:23:90:ea:28  |
|          | vnet0         | cobbler   | 8           | 52:54:00:5a:a9:2c  |
|          | vnet4         | nuage-dns | 4           | 52:54:00:db:45:92  |
| br1      | eno2          |           |             | 28:80:23:90:ea:29  |
|          | vnet1         | cobbler   | 8           | 52:54:00:9b:c2:dc  |
| br999    | eno2.999@eno2 |           |             | 28:80:23:90:ea:29  |
+----------+---------------+-----------+-------------+--------------------+
```
