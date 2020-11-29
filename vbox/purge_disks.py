#!/usr/bin/env python3
#
# Purge inaccessible disks in VirtualBox.
#
import subprocess


def main():
    output = subprocess.check_output(['VBoxManage', 'list', 'hdds'], encoding='utf8', text=True)
    lines = output.splitlines()
    purged = False
    for line in lines:
        if line.startswith('UUID:'):
            uuid = line.split(':')[1].strip()
        elif 'State' in line and 'inaccessible' in line:
            print('Deleting dead disk {uuid}...'.format(uuid=uuid))
            subprocess.run(['VBoxManage', 'closemedium', 'disk', uuid, '--delete'])
            purged = True
    if not purged:
        print('Found no inaccessible disks')


if __name__ == '__main__':
    main()

# $ VBoxManage list hdds
# UUID:           bfbb45ba-d449-4f0f-88a3-f6bdb7726ee7
# Parent UUID:    base
# State:          inaccessible
# Type:           normal (base)
# Location:       /Users/nfiedler/VirtualBox/MicroOS/home.vdi
# Storage format: VDI
# Capacity:       0 MBytes
# Encryption:     disabled
