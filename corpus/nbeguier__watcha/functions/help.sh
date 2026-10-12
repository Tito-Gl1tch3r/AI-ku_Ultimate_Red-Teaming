#!/bin/bash

function help_22 {
    if grep -q '22/OPEN/ssh' /tmp/.watcha.output; then
        echo "${YELLOW}SSH help:${NATIVE}"
    fi
    while read -r line
    do
        if [[ "${line}" != *'22/OPEN/ssh'* ]]; then
            continue
        fi
        ipaddress=$(echo "${line}" | awk '{print $1}')
        if $VERBOSE; then echo ">> " curl -sLk --connect-timeout 2 --max-time 2 -A '""' http://"${ipaddress}":22/ 2>/dev/null; fi
        echo "    [GET] ${ipaddress}  ==> ${BLUE}$(curl -sLk --connect-timeout 2 --max-time 2 -A \"\" http://"${ipaddress}":22/ 2>/dev/null)${NATIVE}"
    done < /tmp/.watcha.output
}

function help_80 {
    if grep -q ' 80/OPEN/http' /tmp/.watcha.output; then
        echo "${YELLOW}HTTP help:${NATIVE}"
    fi
    while read -r line
    do
        if [[ "${line}" != *' 80/OPEN/http'* ]]; then
            continue
        fi
        ipaddress=$(echo "${line}" | awk '{print $1}')
        if $VERBOSE; then echo ">> " curl -sILk  --connect-timeout 2 --max-time 2 -A '""' http://"${ipaddress}":80/ "| grep 'Server: ' | tail -1"; fi
        echo "    [HEAD] http://${ipaddress}:80/  ==> ${BLUE}$(curl -sILk  --connect-timeout 2 --max-time 2 -A \"\" http://"${ipaddress}":80/ | grep 'Server: ' | tail -1)${NATIVE}"
    done < /tmp/.watcha.output
}

function help_443 {
    if grep -q '443/OPEN/https' /tmp/.watcha.output; then
        echo "${YELLOW}HTTPS help:${NATIVE}"
    fi
    while read -r line
    do
        if [[ "${line}" != *'443/OPEN/https'* ]]; then
            continue
        fi
        ipaddress=$(echo "${line}" | awk '{print $1}')
        if $VERBOSE; then echo ">> " curl -sILk  --connect-timeout 2 --max-time 2 -A '""' https://"${ipaddress}":443/ "| grep 'Server: ' | tail -1"; fi
        echo "    [HEAD] https://${ipaddress}:443/  ==> ${BLUE}$(curl -sILk --connect-timeout 2 --max-time 2 -A \"\" https://"${ipaddress}":443/ | grep 'Server: ' | tail -1)${NATIVE}"
        if $VERBOSE; then echo ">> " curl -vsk  --connect-timeout 2 --max-time 2 -A '""' https://"${ipaddress}":443/ " 2>&1 >/dev/null | grep 'subject: ' | tail -1"; fi
        echo "    [GET] https://${ipaddress}:443/  ==> ${BLUE}$(curl -vsk --connect-timeout 2 --max-time 2 -A \"\" https://"${ipaddress}":443/ 2>&1 >/dev/null | grep 'subject: ' | tail -1)${NATIVE}"
    done < /tmp/.watcha.output
}

function help_445 {
    if grep -q '445/OPEN/microsoft-ds' /tmp/.watcha.output; then
        echo "${YELLOW}SAMBA help:${NATIVE}"
    fi
    while read -r line
    do
        if [[ "${line}" != *'445/OPEN/microsoft-ds'* ]]; then
            continue
        fi
        ipaddress=$(echo "${line}" | awk '{print $1}')
        if $VERBOSE; then echo ">> " smbclient -L //"${ipaddress}" -U guest --no-pass; fi
        echo "    smbclient -L //${ipaddress} -U guest --no-pass  ==> $(smbclient -L //"${ipaddress}" -U guest --no-pass >/dev/null 2>&1 && echo -e "${GREEN}" smbclient //"${ipaddress}"/\<Sharename\> -U guest --no-pass)${NATIVE}"
    done < /tmp/.watcha.output
}

function help_2049 {
    if grep -q '2049/OPEN/nfs' /tmp/.watcha.output; then
        echo "${YELLOW}NFS help:${NATIVE}"
    fi
    while read -r line
    do
        if [[ "${line}" != *'2049/OPEN/nfs'* ]]; then
            continue
        fi
        ipaddress=$(echo "${line}" | awk '{print $1}')
        if $VERBOSE; then echo ">>  showmount -e ${ipaddress}"; fi
        echo "    showmount -e ${ipaddress}  ==> ${BLUE}$(showmount -e "${ipaddress}")${NATIVE}"
    done < /tmp/.watcha.output
}

function help_8080 {
    if grep -q '8080/OPEN/http-proxy' /tmp/.watcha.output; then
        echo "${YELLOW}HTTP-PROXY help:${NATIVE}"
    fi
    while read -r line
    do
        if [[ "${line}" != *'8080/OPEN/http-proxy'* ]]; then
            continue
        fi
        ipaddress=$(echo "${line}" | awk '{print $1}')
        if $VERBOSE; then echo ">> " curl -sILk  --connect-timeout 2 --max-time 2 -A '""' http://"${ipaddress}":8080/ "| grep 'Server: ' | tail -1"; fi
        echo "    [HEAD] http://${ipaddress}:8080/  ==> ${BLUE}$(curl -sILk --connect-timeout 2 --max-time 2 -A \"\" http://"${ipaddress}":8080/ | grep 'Server: ' | tail -1)${NATIVE}"
    done < /tmp/.watcha.output
}

function help_9000 {
    if grep -q '9000/OPEN/cslistener' /tmp/.watcha.output; then
        echo "${YELLOW}Port 9000 help:${NATIVE}"
    fi
    while read -r line
    do
        if [[ "${line}" != *'9000/OPEN/cslistener'* ]]; then
            continue
        fi
        ipaddress=$(echo "${line}" | awk '{print $1}')
        if $VERBOSE; then echo ">> " curl -sILk  --connect-timeout 2 --max-time 2 -A '""' http://"${ipaddress}":9000/ "| grep 'Server: ' | tail -1"; fi
        echo "    [HEAD] http://${ipaddress}:9000/  ==> ${BLUE}$(curl -sILk --connect-timeout 2 --max-time 2 -A \"\" http://"${ipaddress}":9000/ | grep 'Server: ' | tail -1)${NATIVE}"
        if $VERBOSE; then echo ">> " curl -sILk  --connect-timeout 2 --max-time 2 -A '""' https://"${ipaddress}":9000/ "| grep 'Server: ' | tail -1"; fi
        echo "    [HEAD] https://${ipaddress}:9000/  ==> ${BLUE}$(curl -sILk --connect-timeout 2 --max-time 2 -A \"\" https://"${ipaddress}":9000/ | grep 'Server: ' | tail -1)${NATIVE}"
        if $VERBOSE; then echo ">> " curl -vsk  --connect-timeout 2 --max-time 2 -A '""' https://"${ipaddress}":9000/ " 2>&1 >/dev/null | grep 'subject: ' | tail -1"; fi
        echo "    [GET] https://${ipaddress}:9000/  ==> ${BLUE}$(curl -vsk --connect-timeout 2 --max-time 2 -A \"\" https://"${ipaddress}":9000/ 2>&1 >/dev/null | grep 'subject: ' | tail -1)${NATIVE}"
    done < /tmp/.watcha.output
}

function help_mac {
    if grep -q 'OPEN' /tmp/.watcha.output; then
        echo "${YELLOW}MAC help:${NATIVE}"
    fi
    while read -r line
    do
        if [[ "${line}" != *'OPEN'* ]]; then
            continue
        fi
        ipaddress=$(echo "${line}" | awk '{print $1}')
        echo "${ipaddress}"
        if [ -n "${SPOOF}" ]; then
            if $VERBOSE; then echo ">> " sudo nmap -sS -Pn -n -S "${SPOOF}" -e "${DEV}" "${ipaddress}" -p 1 "| grep 'MAC Address: '"; fi
            sudo nmap -sS -Pn -n -S "${SPOOF}" -e "${DEV}" "${ipaddress}" -p 1 | grep 'MAC Address: '
        else
            if $VERBOSE; then echo ">> " sudo nmap -sS -Pn -n "${ipaddress}" -p 1 "| grep 'MAC Address: '"; fi
            sudo nmap -sS -Pn -n "${ipaddress}" -p 1 | grep 'MAC Address: '
        fi
    done < /tmp/.watcha.output
}
