#!/bin/bash

function printhelp() {
        echo "Usage: $0 -m MODE -d DOMAIN -u USERNAME"
}

if [ $# -eq 0 ]; then
        printhelp
        exit 1
fi

while getopts "hm:d:u:" option; do
  case $option in
    m) # mode
      mode="$OPTARG"
      ;;
    d) # domain
      domain="$OPTARG"
      ;;
    u) # username
      username="$OPTARG"
      ;;
    h) # help
     printhelp
      ;;
    \?) # invalid option
      printhelp
      echo "Invalid option: -$OPTARG" >&2
      exit 1
      ;;
  esac
done

if [ -z $mode ]; then
        echo "mode required, valid options: domain, user"
        printhelp
        exit 1
fi

if [ -z $domain ]; then
        echo "domain required"
        printhelp
        exit 1
fi

timestamp=`date +"%Y%m%d-%H%M%S"`
format=xml

echo "Collecting tenant info..."
tenantid=$(curl -s https://login.microsoftonline.com/$domain/v2.0/.well-known/openid-configuration | cut -d "\"" -f 4 | cut -d "/" -f 4)
echo "TenantID=$tenantid" | tee -a az-recon-$domain-$timestamp.txt

echo "Collecting realm info..."
realminfo=$(curl -s "https://login.microsoftonline.com/getuserrealm.srf?login=$domain&$format=1")
touch az-recon-$domain-$timestamp.txt
echo "RealmInfo:"
echo $realminfo >> az-recon-$domain-$timestamp.txt
echo "Parsed realm info:" >> az-recon-$domain-$timestamp.txt
domainname=$(echo $realminfo | grep -oE '<DomainName>(.*)<\/DomainName>' | cut -d "<" -f 2 | cut -d ">" -f 2)
echo "DomainName=$domainname" | tee -a az-recon-$domain-$timestamp.txt
namespacetype=$(echo $realminfo | grep -oE '<NameSpaceType>(.*)<\/NameSpaceType>' | cut -d "<" -f 2 | cut -d ">" -f 2)
echo "NameSpaceType=$namespacetype" | tee -a az-recon-$domain-$timestamp.txt
fedbrandname=$(echo $realminfo | grep -oE '<FederationBrandName>(.*)<\/FederationBrandName>' | cut -d "<" -f 2 | cut -d ">" -f 2)
echo "FedBrandName=$fedbrandname" | tee -a az-recon-$domain-$timestamp.txt
if [ "$namespacetype" == "Federated" ]; then
	authurl=$(echo $realminfo | grep -oE '<AuthURL>(.*)<\/AuthURL>' | cut -d "<" -f 2 | cut -d ">" -f 2)
	echo "AuthURL=$authurl" | tee -a az-recon-$domain-$timestamp.txt
	stsauthurl=$(echo $realminfo | grep -oE '<STSAuthURL>(.*)<\/STSAuthURL>' | cut -d "<" -f 2 | cut -d ">" -f 2)
	echo "STSAuthURL=$stsauthurl" | tee -a az-recon-$domain-$timestamp.txt
fi

# Do we need to run user enumeration?
if [ $mode == "user" ]; then
	if [ $namespacetype == "Managed" ]; then
		if [ -z $username ]; then
			echo "No username provided, domain is Managed so user enumeration may be possible" | tee -a az-recon-$domain-$timestamp.txt
		else
			echo "Username provided, checking $username@$domain" | tee -a az-recon-$domain-$timestamp.txt
			usercheck=$(curl -s -X POST "https://login.microsoftonline.com/common/GetCredentialType" --data "{\"Username\":\"$username@$domain\"}")
			echo "GetCredentialType:" >> az-recon-$domain-$timestamp.txt
			echo $usercheck >> az-recon-$domain-$timestamp.txt
			ifuserexists=$(echo $usercheck | grep -oE "IfExistsResult\":[0-9]," | cut -d ":" -f 2 | cut -d "," -f 1)
			echo "IfUserExists=$ifuserexists" | tee -a az-recon-$domain-$timestamp.txt
			# The following may not be accurate for federated domains
			# 1 - Does not exist in tenant
			# 0 - Exists in tenant, auth via Azure
			if [ $ifuserexists == 0 ]; then
				echo "User $username exists in $domain ($tenantid)" | tee -a az-recon-$domain-$timestamp.txt
			elif [ $ifuserexists -eq 1 ]; then
				echo "User $username does NOT exist in $domain ($tenantid)" | tee -a az-recon-$domain-$timestamp.txt
			else
				echo "Unmapped result: $ifuserexists; User $username might not exist in $domain ($tenantid)" | tee -a az-recon-$domain-$timestamp.txt
			fi
		fi
	else
		echo "Domain is not 'Managed', skipping user enumeration checks" | tee -a az-recon-$domain-$timestamp.txt
	fi
fi

echo "Done."
