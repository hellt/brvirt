import subprocess
import re
# from pprint import pprint
import os
# from timeit import default_timer as timer
# https://bitbucket.org/astanin/python-tabulate
from tabulate import tabulate

# TODO: test https://robpol86.github.io/terminaltables/githubtable.html for table geberation

# https://serverfault.com/questions/396105/is-there-a-way-to-determine-which-virtual-interface-belongs-to-a-virtual-machine

# a dict to hold IP interface related info
# got populated by getIfacesData() func.
ifaces = {}

# a set of bridge interfaces itself.
# got populated by the subroutine inside getIfacesData
active_br_ifaces = set()

virsh_ver = ''

# a dict to hold KVM VMs and theirs params
# populated by get_vm_data() func.
vms = {}


def getIfacesData():
    """
    Function parses iproute2 show command `ip address`
    and builds a dict with disctinct interfaces and their properties. For example
    {'br0': {'inet_addr': '172.17.14.6/21',
         'linkstate': 'UP',
         'mac': '28:80:23:90:ea:28',
         'master_bridge': 'self',
         'name': 'br0'},
     'vnet0': {'inet_addr': None,
               'linkstate': 'UP',
               'mac': '28:80:23:90:ea:28',
               'is_virtual': True,
               'master_bridge': 'br0',
               'name': 'vnet0'},
    }

    """

    ipaddr_data = subprocess.check_output(['ip', 'address'], universal_newlines=True)

    # https://regex101.com/r/No99VP/1
    ipconfig_patt = re.compile(r'\s(\S+?):\s(.+?)(?:\n\d+?:|$)', re.DOTALL)

    ifname_patt = re.compile(r'^\d+:\s(\S+):')
    linkstate_patt = re.compile(r'state (UP|DOWN|UNKNOWN)')
    mac_patt = re.compile(r'ether\s(\S+)')
    br_patt = re.compile(r'master\s(\S+)')
    inet_patt = re.compile(r'inet\s(\S+)')

    for iface_name, iface_data in ipconfig_patt.findall(ipaddr_data):

        ifaces.setdefault(iface_name, {})['name'] = iface_name

        linkstate = linkstate_patt.search(iface_data).group(1)
        ifaces[iface_name]['linkstate'] = linkstate

        try:
            mac = mac_patt.search(iface_data).group(1)
        except AttributeError:
            mac = None
        ifaces[iface_name]['mac'] = mac

        try:
            inet_addr = inet_patt.search(iface_data).group(1)
        except AttributeError:
            inet_addr = None
        ifaces[iface_name]['inet_addr'] = inet_addr

        try:
            master_bridge = br_patt.search(iface_data).group(1)
        except AttributeError:
            master_bridge = None
        ifaces[iface_name]['master_bridge'] = master_bridge

        # set is_virtual property for every interface as False
        # later virtual interfaces will overwrite this field with True value
        # inside get_vm_data() function
        ifaces[iface_name]['is_virtual'] = False

    # ifaces_raw_data = {}
    # ifname = ''
    #
    # for line in ipaddr_data.split('\n'):
    #     if ifname:
    #         ifaces_raw_data[ifname] += line
    #
    #     if 'mtu' in line:
    #         ifname = line.split(':')[1].replace(' ', '')
    #         ifaces_raw_data[ifname] = line
    #

    for iface in ifaces:
        if ifaces[iface]['master_bridge'] is not None:
            active_br_ifaces.add(ifaces[iface]['master_bridge'])

    for br_if in active_br_ifaces:
        ifaces[br_if]['master_bridge'] = 'self'


def get_vm_data():
    """
    Thi function uses virsh commands to build a data structure for VMs
    and its network interfaces. For example:

    {'4': {'net_ifaces': {'vnet4': {'if_mac': '52:54:00:db:45:92',
                                'if_master_bridge': 'br0',
                                'if_type': 'virtio'}},
           'vm_name': 'nuage-dns'},
     '8': {'net_ifaces': {'vnet0': {'if_mac': '52:54:00:5a:a9:2c',
                                    'if_master_bridge': 'br0',
                                    'if_type': 'virtio'},
                          'vnet1': {'if_mac': '52:54:00:9b:c2:dc',
                                    'if_master_bridge': 'br1',
                                    'if_type': 'virtio'}},
           'vm_name': 'cobbler'}}

    """
    active_vm_patt = re.compile(r'(\d+)\s+(\S+)')
    # get active vm_id, vm_name pairs: [('4', 'nuage-dns'), ('8', 'cobbler')]
    active_vm_list = subprocess.check_output('virsh list | tail -n +3', shell=True, universal_newlines=True)

    for virsh_vm in active_vm_patt.findall(active_vm_list):
        vms[virsh_vm[0]] = {
            'dom_id': virsh_vm[0],
            'vm_name': virsh_vm[1]
        }

    # pattern to match every propery of an interface in virsh domiflist command
    domif_patt = re.compile(r'\S+')
    for dom_id, dom_data in vms.items():
        vms[dom_id]['net_ifaces'] = {}
        domiflist = subprocess.check_output('virsh domiflist {} | tail -n +3'.format(dom_id), shell=True, universal_newlines=True)
        for l in domiflist.split('\n'):
            if l.split():   # skipping empty lines
                domif_data = domif_patt.findall(l)

                # update globally visible ifaces with is_virtual property
                # for VM interfaces
                ifaces[domif_data[0]]['is_virtual'] = True

                # populate vms{} with interface properties
                vms[dom_id]['net_ifaces'][domif_data[0]] = {'if_type': domif_data[1],
                                                            'if_master_bridge': domif_data[2],
                                                            'if_type': domif_data[3],
                                                            'if_mac': domif_data[4]}


def get_br_ifaces(brname):
    bridge_ifaces = []
    for iface in ifaces:
        if ifaces[iface]['master_bridge'] == brname:
            bridge_ifaces.append(iface)
    return sorted(bridge_ifaces)


def show_bridge(brname):
    for iface in ifaces:
        if ifaces[iface]['master_bridge'] == brname:
            print('bridge {} has {} interface attached'.format(brname, iface))


def is_virsh_installed():
    try:
        virsh_ver = subprocess.check_output(["virsh", "--version"], universal_newlines=True)
        # print('virsh version {} is found'.format(virsh_ver))
    except OSError as e:
        if e.errno == os.errno.ENOENT:
            print('virsh is not found and this script relies on it. Exiting...')
            exit(code=1)


def get_vm_by_iface(ifname):
    for dom_id in vms:
        if ifname in vms[dom_id]['net_ifaces']:
            return vms[dom_id]
    return ''  # return if not a vm interface


def show():
    table_data = []
    for br in sorted(active_br_ifaces):
        row = []
        row.append(br)
        for iface in get_br_ifaces(br):
            if not row:
                row = ['']
            row.append(iface)   # interface name

            # for virtual interfaces get vm_name and dom_id
            if ifaces[iface]['is_virtual']:
                vm = get_vm_by_iface(iface)
                row.append(vm['vm_name'])
                row.append(vm['dom_id'])
            else:  # otherwise add blanks
                row.extend(('', ''))

            # for virtual interfaces get mac address
            # from vms{} data structure rather than ifaces{} because they do differ
            if ifaces[iface]['is_virtual']:
                row.append(vm['net_ifaces'][iface]['if_mac'])
            else:
                row.append(ifaces[iface]['mac'])
            table_data.append(row)
            row = []
    t_headers = ['Bridge', 'Interface', 'VM name', 'Domain ID', 'Int. MAC address']

    print(tabulate(table_data, headers=t_headers, tablefmt="psql"))


is_virsh_installed()

getIfacesData()

get_vm_data()

show()
