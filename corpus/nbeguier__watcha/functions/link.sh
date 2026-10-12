#!/bin/bash

function link_21 {
    if grep -q '21/OPEN/ftp' /tmp/.watcha.output; then
        echo "${YELLOW}FTP link:${NATIVE}"
        grep '21/OPEN/ftp' /tmp/.watcha.output | awk '{print "    tools/ftp.sh "$1" admin password"}'
    fi
}

function link_22 {
    if grep -q '22/OPEN/ssh' /tmp/.watcha.output; then
        echo "${YELLOW}SSH link:${NATIVE}"
        grep '22/OPEN/ssh' /tmp/.watcha.output | awk '{print "    ssh -l root -i /dev/null "$1}'
    fi
}

function link_80 {
    if grep -q ' 80/OPEN/http' /tmp/.watcha.output; then
        echo "${YELLOW}HTTP link:${NATIVE}"
        grep ' 80/OPEN/http' /tmp/.watcha.output | awk '{print "    curl -A \"\" http://"$1":80/ >/dev/null -vs"}'
    fi
}

function link_443 {
    if grep -q '443/OPEN/https' /tmp/.watcha.output; then
        echo "${YELLOW}HTTPS link:${NATIVE}"
        grep '443/OPEN/https' /tmp/.watcha.output | awk '{print "    curl -kA \"\" https://"$1":443/ >/dev/null -vs"}'
    fi
}

function link_445 {
    if grep -q '445/OPEN/microsoft-ds' /tmp/.watcha.output; then
        echo "${YELLOW}SAMBA link:${NATIVE}"
        grep '445/OPEN/microsoft-ds' /tmp/.watcha.output | awk '{print "    tools/samba.sh "$1}'
    fi
}

function link_2049 {
    if grep -q '2049/OPEN/nfs' /tmp/.watcha.output; then
        echo "${YELLOW}NFS link:${NATIVE}"
        grep '2049/OPEN/nfs' /tmp/.watcha.output | awk '{print "    showmount -e "$1"; mkdir /tmp/export; mount -t nfs "$1":/PATH /tmp/export"}'
    fi
}

function link_8080 {
    if grep -q '8080/OPEN/http-proxy' /tmp/.watcha.output; then
        echo "${YELLOW}HTTP-PROXY link:${NATIVE}"
        grep '8080/OPEN/http-proxy' /tmp/.watcha.output | awk '{print "    curl -A \"\" http://"$1":8080/ >/dev/null -vs"}'
    fi
}

function link_9000 {
    if grep -q '9000/OPEN/cslistener' /tmp/.watcha.output; then
        echo "${YELLOW}Port 9000 link:${NATIVE}"
        grep '9000/OPEN/cslistener' /tmp/.watcha.output | awk '{print "    curl -A \"\" http://"$1":9000/ >/dev/null -vs"}'
    fi
}
