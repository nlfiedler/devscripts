#!/bin/sh
#
# Set up a VirtualBox VM to be used with OpenIndiana/Solaris.
#

VMNAME='oi151a8'
VDI="/Users/nfiedler/VirtualBox VMs/$VMNAME/$VMNAME.vdi"
ISO='/Users/nfiedler/Downloads/oi-dev-151a8-text-x86.iso'

if [ ! -f "$ISO" ]; then
    echo "Missing ISO image $ISO"
    exit 1
fi

VBoxManage list vms | grep $VMNAME > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "VM $VMNAME already exists"
    exit 1
fi

echo 'Creating VirtualBox VM...'
VBoxManage createvm --name $VMNAME --register
VBoxManage modifyvm $VMNAME --ostype Solaris11_64 --memory 4096
#VBoxManage modifyvm $VMNAME --vrde on --vrdeport 5800-5808
VBoxManage modifyvm $VMNAME --vram 16
VBoxManage modifyvm $VMNAME --nic1 nat
VBoxManage modifyvm $VMNAME --nictype1 82540EM
VBoxManage modifyvm $VMNAME --natpf1 ssh,tcp,,2222,,22
if [ ! -f "$VDI" ]; then
    VBoxManage createhd --filename "$VDI" --size 102400 --variant Standard
fi
VBoxManage storagectl $VMNAME --name "IDE Controller" --add ide --controller PIIX4
VBoxManage storageattach $VMNAME --storagectl "IDE Controller" --port 0 --device 0 --type hdd --medium "$VDI"
VBoxManage storageattach $VMNAME --storagectl "IDE Controller" --port 0 --device 1 --type dvddrive --medium "$ISO"
echo 'VM creation complete'
