#!/bin/bash

#### Script to install RSYSLOG, AUDITD, and configure host to send logs to a SYSLOG server ####

#### GLOBAL VARIABLES ####

SENSORIP="<IP OF SYSLOG SERVER OR SIEM>"
AUDIT_RULE_URL="https://raw.githubusercontent.com/Hacks4Snacks/linux-auditd/master/audit.rules" # Links to rule file in repository

#### SCRIPT ACTIONS ####

if [[ "$1" == "--uninstall" ]]; then
    do_uninstall=true
else
    do_install_auditd=true
    do_install_rsyslog=true
fi

#### OS VERIFICATION ####

if [[ -f /etc/os-release ]]; then
    source /etc/os-release
    elif [[ -f /etc/redhat-release ]]; then
    NAME=$(sed -rn 's/(\w+).*/\1/p' /etc/redhat-release)
    VERSION_ID=$(grep -o '[0-9]\.[0-9]' /etc/redhat-release)
else
    echo "Can not identify OS"
    exit 1
fi

if [[ "${NAME}" == "Ubuntu"  ]]; then
    UBUNTU=true
    elif [[ "${NAME}" == *"SUSE"* ]]; then
    SUSE=true
    elif [[ "${NAME}" == "CentOS Linux" ]]; then
    CENTOS=true
    elif [[  -f /etc/redhat-release ]]; then
    if [[ "${NAME}" == "CentOS" ]]; then
        CENTOS=true
        elif [[ "${NAME}" == "Red"* ]]; then
        #        Treat redhat like centos
        CENTOS=true
    fi
fi

unset sudo

if [[ "$EUID" != "0" ]]; then
    sudo=sudo
fi

#### INSTALL FUNCTIONS ####

install_auditd() {
    if [[ "${UBUNTU}" == "true" ]]; then
        install_auditd_ubuntu
        elif [[ "${SUSE}" == "true" ]]; then
        install_auditd_suse
        elif [[ "${CENTOS}" == "true" ]]; then
        install_auditd_centos
    fi
}

install_auditd_ubuntu() {
    if ! dpkg -s auditd &> /dev/null; then
    	${sudo} apt-get update > /dev/null 2>&1
        ${sudo} apt-get install auditd audispd-plugins -y > /dev/null 2>&1
        setup_auditd_ubuntu
    else
        ${sudo} systemctl stop auditd > /dev/null 2>&1
        setup_auditd_ubuntu
    fi
}

install_auditd_suse() {
    if ! rpm -q audit &> /dev/null; then
        ${sudo} zypper refresh > /dev/null 2>&1
        ${sudo} zypper install audit -y > /dev/null 2>&1
        setup_auditd_suse
    else
        ${sudo} systemctl stop auditd > /dev/null 2>&1
        setup_auditd_suse
    fi
}

install_auditd_centos() {
    if ! rpm -q audit &> /dev/null; then
        #${sudo} yum update > /dev/null 2>&1
        ${sudo} yum install -y audit > /dev/null 2>&1
        setup_auditd_centos
    else
        ${sudo} service auditd stop > /dev/null 2>&1
        setup_auditd_centos
    fi
}

install_rsyslog() {
    if [[ "${UBUNTU}" == "true" ]]; then
        install_rsyslog_ubuntu
        elif [[ "${SUSE}" == "true" ]]; then
        install_rsyslog_suse
        elif [[ "${CENTOS}" == "true" ]]; then
        install_rsyslog_centos
    fi
}

install_rsyslog_ubuntu() {
    if ! dpkg -s auditd &> /dev/null; then
        ${sudo} apt-get update > /dev/null 2>&1
        ${sudo} apt-get install rsyslog -y > /dev/null 2>&1
        setup_rsyslog_ubuntu
    else
        ${sudo} systemctl stop rsyslog > /dev/null 2>&1
        setup_rsyslog_ubuntu
    fi
}

install_rsyslog_suse() {
    if ! rpm -q audit &> /dev/null; then
        ${sudo} zypper refresh > /dev/null 2>&1
        ${sudo} zypper install rsyslog -y > /dev/null 2>&1
        setup_rsyslog_suse
    else
        ${sudo} systemctl stop rsyslog > /dev/null 2>&1
        setup_rsyslog_suse
    fi
}

install_rsyslog_centos() {
    if ! rpm -q audit &> /dev/null; then
        #${sudo} yum update > /dev/null 2>&1
        ${sudo} yum install -y rsyslog > /dev/null 2>&1
        setup_rsyslog_centos
    else
        ${sudo} systemctl stop rsyslog > /dev/null 2>&1
        setup_rsyslog_centos
    fi
}

#### SETUP FUNCTIONS (CONFIGURE) ####

setup_auditd()
{
    ${sudo} wget -q -O /tmp/audit.rules ${AUDIT_RULE_URL}
    ${sudo} cp /tmp/audit.rules /etc/audit/rules.d/
    ${sudo} sed -i 's/active = no/active = yes/' /etc/audisp/plugins.d/syslog.conf
    ${sudo} sed -i 's/args = LOG_INFO/args = LOG_LOCAL6/' /etc/audisp/plugins.d/syslog.conf
}

setup_auditd_ubuntu()
{
    setup_auditd
    ${sudo} systemctl enable auditd > /dev/null 2>&1
    ${sudo} systemctl start auditd > /dev/null 2>&1
}

setup_auditd_suse()
{
    setup_auditd
    ${sudo} systemctl enable auditd > /dev/null 2>&1
    ${sudo} systemctl start auditd > /dev/null 2>&1
}

setup_auditd_centos()
{
    setup_auditd
    ${sudo} systemctl enable auditd > /dev/null 2>&1
    ${sudo} systemctl start auditd > /dev/null 2>&1
}

setup_rsyslog_ubuntu()
{
    #    read -p "Please enter the IP of the USM Sensor: " SENSORIP
    ${sudo} echo "*.*    @${SENSORIP}:514" | sudo tee -a /etc/rsyslog.d/50-default.conf > /dev/null
    ${sudo} systemctl enable rsyslog > /dev/null 2>&1
    ${sudo} systemctl start rsyslog > /dev/null 2>&1
}

setup_rsyslog_suse()
{
    #    read -p "Please enter the IP of the USM Sensor: " SENSORIP
    ${sudo} echo "*.*    @${SENSORIP}:514" | sudo tee -a /etc/rsyslog.d/50-default.conf > /dev/null
    ${sudo} systemctl enable rsyslog > /dev/null 2>&1
    ${sudo} systemctl start rsyslog > /dev/null 2>&1
}

setup_rsyslog_centos()
{
    #    read -p "Please enter the IP of the USM Sensor: " SENSORIP
    ${sudo} echo "*.*    @${SENSORIP}:514" | sudo tee -a /etc/rsyslog.d/50-default.conf > /dev/null
    ${sudo} systemctl enable rsyslog > /dev/null 2>&1
    ${sudo} systemctl start rsyslog > /dev/null 2>&1
}

#### UNINSTALL FUNCTIONS ####

uninstall_auditd_ubuntu()
{
    ${sudo} systemctl stop auditd
    ${sudo} systemctl disable auditd
    ${sudo} apt-get purge --auto-remove auditd > /dev/null 2>&1
    ${sudo} rm -rf /etc/audit > /dev/null 2>&1
    ${sudo} rm -rf /etc/audisp > /dev/null 2>&1
    ${sudo} rm -rf /var/log/audit > /dev/null 2>&1
}

uninstall_auditd_suse()
{
    ${sudo} systemctl stop auditd
    ${sudo} systemctl disable auditd
    ${sudo} zypper remove -y audit > /dev/null 2>&1
    ${sudo} rm -rf /etc/audit > /dev/null 2>&1
    ${sudo} rm -rf /etc/audisp > /dev/null 2>&1
    ${sudo} rm -rf /var/log/audit > /dev/null 2>&1
}

uninstall_auditd_centos()
{
    ${sudo} systemctl stop auditd
    ${sudo} systemctl disable auditd
    ${sudo} yum remove -y audit > /dev/null 2>&1
    ${sudo} rm -rf /etc/audit > /dev/null 2>&1
    ${sudo} rm -rf /etc/audisp > /dev/null 2>&1
    ${sudo} rm -rf /var/log/audit > /dev/null 2>&1
}

auditd_uninstall()
{
    if [[ "${UBUNTU}" == "true" ]]; then
        uninstall_auditd_ubuntu
        elif [[ "${SUSE}" == "true" ]]; then
        uninstall_auditd_suse
        elif [[ "${CENTOS}" == "true" ]]; then
        uninstall_auditd_centos
    fi
}

#### SCRIPT RUN ####

if [ "$do_install_auditd" = true ] ; then
    install_auditd
    ${sudo} systemctl restart auditd > /dev/null 2>&1
fi

if [ "$do_install_rsyslog" = true ] ; then
    install_rsyslog
    ${sudo} systemctl restart rsyslog > /dev/null 2>&1
fi

if [ "$do_uninstall" = true ] ; then
    auditd_uninstall
fi
