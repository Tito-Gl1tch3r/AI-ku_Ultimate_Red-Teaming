#!/bin/bash

function get_ip {
    ip a show dev "${DEV}" | grep 'inet ' | awk '{print $2}'
}

function get_ip_simple {
    get_ip | awk -F/ '{print $1}'
}

function get_rand_ip_complex {
    for last_octet in $(seq 1 254)
    do
        IP_CANDIDATE=$(get_ip_simple | awk -F. -v var="$last_octet" '{print $1"."$2"."$3"."var}')
        if ! ping -c 1 -W 1 "${IP_CANDIDATE}" >/dev/null 2>&1; then
            echo "${IP_CANDIDATE}"
            break
        fi
    done
}

function get_network {
    ipcalc -n "$(get_ip)" | grep 'Network:' | awk '{print $2}'
}

function get_gateway {
    ip route | grep "${DEV}" | grep default | awk '{print $3}'
}

function get_n_24 {
    SUBNET_SIZE=$1
    if [ "${SUBNET_SIZE}" -ge 24 ]; then
        echo 1
    else
        echo 2 ^ \(24 - "${SUBNET_SIZE}"\) | bc
    fi
}

function get_subnetwork {
    NETMASK=$(get_ip | awk -F/ '{print $2}')
    N_24=$(get_n_24 "${NETMASK}")
    if [ "${N_24}" -gt 32 ]; then
        echo "Too much subnet"
        exit 1
    elif [ "${N_24}" -ne 1 ]; then
        # Fonction pour convertir une adresse IP en entier
        ip2int() {
            local IFS=.
            read -r a b c d <<< "$1"
            echo $(( (a << 24) | (b << 16) | (c << 8) | d ))
        }

        # Fonction pour convertir un entier en adresse IP
        int2ip() {
            local ip=$1
            echo "$(( (ip >> 24) & 0xFF )).$(( (ip >> 16) & 0xFF )).$(( (ip >> 8) & 0xFF )).$(( ip & 0xFF ))"
        }

        # Conversion de l'adresse de base
        BASE=$(ip2int $(get_network))

        # Le nombre de /24 dans une /21 est de 2^(24-21)=8
        for i in $(seq "${N_24}"); do
            # Pour chaque sous-réseau, ajouter i*256 à l'adresse de base
            NEW_IP=$(int2ip $(( BASE + (i-1) * 256 )))
            echo "$NEW_IP/24"
        done
    else
        get_network
    fi
}

function scan_host {
    echo "" > /tmp/.watcha.output
    echo "... tail -f /tmp/.watcha.output"
    for subnet in $(get_subnetwork)
    do
        if [ -n "${SPOOF}" ]; then
            if $VERBOSE; then echo ">> " sudo nmap -sS -p "${PORTS}" -Pn -n -S "${SPOOF}" -e "${DEV}" "${subnet}"; fi
            sudo nmap -sS -p "${PORTS}" -Pn -n -S "${SPOOF}" -e "${DEV}" -oG /tmp/.watcha.subnet "${subnet}" >/dev/null
        else
            if $VERBOSE; then echo ">> " sudo nmap -sS -p "${PORTS}" -Pn -n "${subnet}"; fi
            sudo nmap -sS -p "${PORTS}" -Pn -n -oG /tmp/.watcha.subnet "${subnet}" >/dev/null
        fi
        grep -v ^# /tmp/.watcha.subnet | grep 'Ports:' | awk '{$1=""; $3=""; $4=""; print $0}' | 
            sed "s#closed/tcp/#closed#g" |
            sed "s#filtered/tcp/#filtered#g" |
            sed "s#open/tcp/#OPEN#g" |
            sed 's#[0-9]*/closed/[a-z\-]*##g' |
            sed 's#,##g' |
            sed "s#///##g" |
            tr -s ' ' >> /tmp/.watcha.output
    done
    sudo rm -f /tmp/.watcha.subnet
    sed "s#OPEN#${GREEN}OPEN${NATIVE}#g" /tmp/.watcha.output
}
