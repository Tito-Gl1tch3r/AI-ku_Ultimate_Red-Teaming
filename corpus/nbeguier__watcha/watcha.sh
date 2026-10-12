#!/bin/bash

ESC=$(printf '\033')
export PORTS='21,22,25,80,443,445,2049,8080,9000'
export BOLD="${ESC}[1m"
export GREEN="${ESC}[92m"
export YELLOW="${ESC}[93m"
export BLUE="${ESC}[94m"
export NATIVE="${ESC}[m"
export VERBOSE=false

function check_binary() {
    if ! command -v "${1}" >/dev/null; then echo "You have to install $1"; exit 1; fi
}

display_usage() {
    echo -e "Usage:\n$0 [-h,--help] [-v,--verbose] [-r,--range range] [-n,--no-spoof] -i interface"
    echo "  -r,--range   nmap target to scan instead of the interface network"
    echo "               (e.g. 10.0.0.0/24, 192.168.1.10-50, \"host1 host2\")"
    echo "  -n,--no-spoof  scan from the real IP instead of a spoofed source"
    echo "               (needed when the range is off the interface network)"
    check_binary ip
    echo "Interfaces available:"
    echo "$(ip a | grep 'status UP' | grep '^[a-z0-9]' | awk -F ':' '{print $1":"$2}')"
}

POSITIONAL=()
while [[ $# -gt 0 ]]
do
key="$1"

case $key in
    -i|--interface)
    DEV="$2"
    shift # past argument
    shift # past value
    ;;
    -r|--range)
    RANGE="$2"
    shift # past argument
    shift # past value
    ;;
    -n|--no-spoof)
    NO_SPOOF=true
    shift # past argument
    ;;
    -h|--help)
    display_usage
    exit 0
    ;;
    -v|--verbose)
    VERBOSE=true
    echo ">> Enable verbosity"
    shift # past argument
    ;;
    *)    # unknown option
    POSITIONAL+=("$1") # save it in an array for later
    shift # past argument
    ;;
esac
done
set -- "${POSITIONAL[@]}" # restore positional parameters

if [  "${DEV}" == '' ]; then
    display_usage
    exit 1
fi

check_binary nmap
check_binary ipcalc
check_binary bc
check_binary sudo
check_binary ip

# shellcheck source=functions/scan.sh
source "$(dirname "${0}")/functions/scan.sh"
# shellcheck source=functions/scan.sh
source "$(dirname "${0}")/functions/link.sh"
# shellcheck source=functions/scan.sh
source "$(dirname "${0}")/functions/help.sh"

if [ "${NO_SPOOF}" == 'true' ]; then
    SPOOF=''
else
    SPOOF=$(get_rand_ip_complex)
fi
IP=$(get_ip)

# Stop if no IP
if [ -z "${IP}" ]; then
    echo "There is no IP address on this interface..."
    exit 1
fi

echo "${BOLD}Device${NATIVE}:     ${DEV}"
echo "${BOLD}IP${NATIVE}:         ${IP}"
echo "${BOLD}Network${NATIVE}:    $(get_network)"
echo "${BOLD}Gateway${NATIVE}:    $(get_gateway)"
echo "${BOLD}Spoofed IP${NATIVE}: ${SPOOF}"

# Use the user-supplied range instead of the interface network
if [ -n "${RANGE}" ]; then
    # Redefinition of get_subnetwork
    function get_subnetwork {
        echo "${RANGE}"
    }
    echo "${BOLD}Range${NATIVE}:      ${RANGE}"
# Stop if network to large
elif [[ "$(get_subnetwork)" == *"Too much subnet"* ]]; then
    echo "Too much subnet..."
    echo "Do you want to reduce the network to a /24 ? (y/N)"
    read -r RESPONSE
    if [[ "${RESPONSE}" != *"y"* ]]; then
        echo "Which /24 do you want to scan ?"
        read -r RESPONSE
        function get_network {
            echo "${RESPONSE}"
        }
    else
        # Redefinition of get_network
        function get_network {
            ipcalc -n "$(get_ip)" | grep 'Network:' | awk '{print $2}' | awk -F'/' '{print $1"/24"}'
        }
    fi
    function get_subnetwork {
        get_network
    }
    echo "${BOLD}Reduced network${NATIVE}:  $(get_network)"
fi

# SCAN
echo ""
echo "${BOLD}====SCAN====${NATIVE}"

scan_host

# LINK
echo ""
echo "${BOLD}====LINK====${NATIVE}"

link_21
link_22
link_80
link_443
link_445
link_2049
link_8080
link_9000

# HELP
echo ""
echo "${BOLD}====HELP====${NATIVE}"

help_22
help_80
help_443
help_445
help_2049
help_8080
help_9000
help_mac
