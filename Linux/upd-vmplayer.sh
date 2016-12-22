#!/bin/bash
#this script can be run from:
#curl -Ls https://git.io/vie2W | bash -s -- -i

trap exit SIGINT SIGTERM SIGKILL

function usage () {
	echo "
		About:
		This script installs and updates the necessary kernel modules for VMware Workstation and the Horizon View Client to work on OpenSUSE Tumbleweed x64.
		It is assumed that you are running this as root.

		Usage: 
		$0 [option]

		Options:
		[-h] Prints this help text.
		[-i] Installs the pre-requisites for Workstation and the View Client, as well as the apps themselves if you don't have them.
		[-u] Updates the kernel modules for Workstation. This will need to be run every time your kernel updates to a new version.
	" | tr -d '\t' | fold -sw $(tput cols)
	exit
}

function update-modules () {
	echo "Compiling Workstation drivers..."
	# Compile VMnet driver
	cd /usr/lib/vmware/modules/source
	tar -xf ./vmnet.tar
#	sed -i.bak 's/get_user_pages/get_user_pages_remote/g' vmnet-only/userif.c
#	sed -i.bak -e 's/dev->trans_start = jiffies/netif_trans_update(dev)/g' vmnet-only/netif.c
	cd vmnet-only
	make clean
	make
	cd ..
	cp ./vmnet.o /lib/modules/`uname -r`/kernel/drivers/misc/vmnet.ko
	rm -fr vmnet-only

	# Compile VMmon driver
	tar -xf ./vmmon.tar
#	sed -i.bak 's/get_user_pages/get_user_pages_remote/g' vmmon-only/linux/hostif.c
	cd vmmon-only
	make clean
	make
	cd ..
	cp vmmon.o /lib/modules/`uname -r`/kernel/drivers/misc/vmmon.ko
	rm -fr vmmon-only
	
	# Reload kernel modules and restart Workstation services
	depmod -a
	/etc/init.d/vmware restart

	echo "If the above succeeded, you should be able to launch Workstation and the View Client without rebooting." | fold -sw $(tput cols)
}

function install-modules () {
	echo "Installing pre-requisites for Workstation and the View Client..."
	zypper install \
		kernel-default \
		kernel-devel \
		kernel-macros \
		kernel-source \
		libatk-1_0-0-32bit \
		libcairo2-32bit \
		libcrypto3? \
		libcrypto3?-32bit \
		libgdk_pixbuf-2_0-0-32bit \
		libgio-2_0-0-32bit \
		libglib-2_0-0-32bit \
		libgmodule-2_0-0-32bit \
		libgobject-2_0-0-32bit \
		libgthread-2_0-0-32bit \
		libgtk-2_0-0-32bit \
		libopenssl1_0_0-32bit \
		libpango-1_0-0-32bit \
		libpcsclite1-32bit \
		libpixman-1-0-32bit \
		libpng12-0-32bit \
		libtheoradec1-32bit \
		libtheoraenc1-32bit \
		libudev1-32bit \
		libudev0 \
		libuuid1-32bit  \
		libv4l2-0-32bit \
		libxml2-2-32bit \
		libXss1-32bit \
		libXtst6-32bit \
		patterns-openSUSE-devel_basis \

	# The View Client looks in the wrong place for some libraries, so we have to link them to the place it expects.
	ln -sv /usr/lib/libcrypto.so.3? /usr/lib/libcrypto.so.1.0.1
	ln -sv /usr/lib/libudev.so.1 /usr/lib/libudev.so.0
	ln -sv /lib/libssl.so.1.0.0 /usr/lib/libssl.so.1.0.1

	if [ ! -x /usr/bin/vmware ]; then
		read -p "It doesn't look like you have Workstation installed. Would you like to install it? (y/N)
		# " choice
		if [[ "$choice" =~ y|Y|yes ]]; then
			wget http://www.vmware.com/go/tryworkstation-linux-64 -O /opt/vmware-workstation-installer
			bash /opt/vmware-workstation-installer --eulas-agreed --console
			update-modules
		fi
	fi

	if [ ! -x /usr/bin/vmware-view ]; then
		read -p "It doesn't look like you have the View Client installed. Would you like to install it? (y/N)
		# " choice
		if [[ "$choice" =~ y|Y|yes ]]; then
			read -p "Be sure to choose 'no' for all the options, as most of them will cause connection failures.
			Press 'enter' to continue.
			# " wait
			wget https://download3.vmware.com/software/view/viewclients/CART16Q2/VMware-Horizon-Client-4.1.0-3976982.x64.bundle -O /opt/vmware-view-client-installer
			bash /opt/vmware-view-client-installer --eulas-agreed --console
		fi
	fi
}

if [ "$USER" != "root" ]; then
	echo "This script must be run as root. Exiting."
	exit
fi

if [ "$*" = "" ]; then
	echo -e "You must specify an option.\nFor usage, type: '$0 -h'"
	exit
fi

while getopts hiu arg ; do
	case $arg in
		h) usage ;;
		i) install-modules ;;
		u) update-modules ;;
		*) echo "For usage, type: '$0 -h'"; exit ;;
	esac
done
