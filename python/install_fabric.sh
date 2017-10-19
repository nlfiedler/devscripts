#!/bin/sh
#
# Create a Python virtualenv and install Fabric. This avoids conflicts with the
# other dependencies that Git Fusion employs.
#

if [ $# -eq 0 ]; then
    echo "Usage: $0 <environment>"
    exit 1
fi
if [ "${VIRTUAL_ENV}" != "" ]; then
    echo 'Deactivate your current environment first!'
    exit 1
fi
VENV=$1

#
# Python 2.7 does not have pyvenv, so must install it (via pip) to get the
# command for creating the virtual environment.
#
if [ ! -e /usr/local/bin/pip2.7 ]; then
    test -f get-pip.py || wget https://bootstrap.pypa.io/get-pip.py
    sudo python2.7 get-pip.py
    rm get-pip.py
fi
sudo /usr/local/bin/pip2.7 install virtualenv
/usr/local/bin/virtualenv $VENV
. ${VENV}/bin/activate
pip install fabric
