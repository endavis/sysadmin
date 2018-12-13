#!/bin/bash
# This is for redhat/oracle servers
# the first argument should be the domain admin user to install as
# the second argument should be the user's password.
fulldomain="$1" # "addomain.com"
shortdomain="$2" # "addomain"
securitygroup="$3" # "Domain Admins"
domainaccount="$4" # domain admin user
domainpass="$5" # domain admin user password

mkdir -p /root/tmp
cd /root/tmp

# add pbis repo
rpm --import http://repo.pbis.beyondtrust.com/yum/RPM-GPG-KEY-pbis
wget -O /etc/yum.repos.d/pbiso.repo http://repo.pbis.beyondtrust.com/yum/pbiso.repo
sudo yum clean all 
sudo yum -y install pbis-open

# latest version as of 11/21/2018
#wget https://github.com/BeyondTrust/pbis-open/releases/download/8.7.1/pbis-open-8.7.1.494.linux.x86_64.rpm.sh

#sh ./pbis-open-8.7.1.494.linux.x86_64.rpm.sh install
cd /opt/pbis/bin/ 
domainjoin-cli join $fulldomain $domainaccount $domainpass

/opt/pbis/bin/config UserDomainPrefix $shortdomain 
/opt/pbis/bin/config AssumeDefaultDomain true 
/opt/pbis/bin/config LoginShellTemplate /bin/bash 
/opt/pbis/bin/config HomeDirTemplate %H/%U 
/opt/pbis/bin/config RequireMembershipOf "$shortdomain\\$securitygroup"
