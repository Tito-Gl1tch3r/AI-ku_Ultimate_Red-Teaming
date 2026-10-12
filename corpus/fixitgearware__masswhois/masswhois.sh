#!/usr/bin/env bash


# Banner Design.

function banner() {
    echo -e  " ##::::'##::::'###:::::'######:::'######::'##:::::'##:'##::::'##::'#######::'####::'######::"
    echo -e " ###::'###:::'## ##:::'##... ##:'##... ##: ##:'##: ##: ##:::: ##:'##.... ##:. ##::'##... ##:"
    echo -e " ####'####::'##:. ##:: ##:::..:: ##:::..:: ##: ##: ##: ##:::: ##: ##:::: ##:: ##:: ##:::..::"
    echo -e " ## ### ##:'##:::. ##:. ######::. ######:: ##: ##: ##: #########: ##:::: ##:: ##::. ######::"
    echo -e " ##. #: ##: #########::..... ##::..... ##: ##: ##: ##: ##.... ##: ##:::: ##:: ##:::..... ##:"
    echo -e " ##:.:: ##: ##.... ##:'##::: ##:'##::: ##: ##: ##: ##: ##:::: ##: ##:::: ##:: ##::'##::: ##:"
    echo -e " ##:::: ##: ##:::: ##:. ######::. ######::. ###. ###:: ##:::: ##:. #######::'####:. ######::"
    echo -e "..:::::..::..:::::..:::......::::......::::...::...:::..:::::..:::.......:::....:::......::"
}

echo ""
echo "" 

# Call Banner Function. 
banner

echo ""
echo "" 

# Usage Display. 
function display_help() {
    
    echo ""
    echo ""
    echo " 'masswhois' 'version one' is a Shell based Script tool created by FixitgearwareSecurity which performs 'whois lookup' "
    echo " for both 'Single/Bulk 'Domain','Subdomain', or 'IP Address' provided by the user of this tool. So what is the goal behind 'MassWhois...?'"
    echo " the Goal is to aid newbies and security researchers who are yet to get familiar in bypassing CDN Firewall Rules, "
    echo " identify these 'Domains','Subdomains', or 'IP Addresses',that are not yet behind a 'CDN', which then gives them further edge in exploiting "
    echo " these findings, using their various scanning tools. Security Researchers who are into network/IP Address hacking will find this tool useful."
    echo ""
    echo ""
    echo "Usage:"
    echo ""
    echo "[Options]:"
    echo ""
    echo "  --help     Display the help message."
    echo ""
    echo "For Batch text-file with domains: 'sudo $0 [domain_list.txt] [output.html]' "
    echo ""
    echo "- Example (batch domain list):"
    echo ""
    echo "sudo $0 domain_list.txt output.html"
    echo ""
    echo "For Single domain Name: 'sudo $0 [domain] [output.html]' "
    echo ""
    echo "- Example (single domain name):"
    echo ""
    echo "sudo $0 example.com output.html"
    exit 0
      
    
}

# Check if --help option is provided
if [[ "$1" == "--help" ]]; then
    display_help
fi

# Check if arguments are provided
if [[ "$#" -ne 2 ]]; then
    echo "Usage: $0 [domain_list.txt] [output.html] or [domain] [output.html]"
    echo "Try '$0 --help' for more information."
    exit 1
fi

input="$1"
output_file="$2"

# Start HTML document
echo "<html><head><title>Whois Results</title><style>body{font-family: Arial, sans-serif;} .domain {margin-bottom: 20px;} pre {background: #f4f4f4; padding: 10px; border-radius: 5px;}</style></head><body>" > "$output_file"
echo "<h1>Whois Results</h1>" >> "$output_file"

# Function to clean domain names
clean_domain() {
    echo "$1" | sed -e 's/^https:\/\///' -e 's/^http:\/\///' -e 's/^www\.//'
}

# Define patterns to remove from WHOIS results
patterns_to_remove=(
    "For more information on Whois status codes, please visit https://icann.org/epp"
    "date of the domain name registrant's agreement with the sponsoring registrar.  Users may consult the sponsoring registrar's Whois database to view the registrar's reported date of expiration for this registration."
    "database through the use of electronic processes that are high-volume and automated except as reasonably necessary to register domain names or information purposes only, and to assist persons in obtaining information guarantee its accuracy. By submitting a Whois query, you agree to abide by the following terms of use: You agree that you may use this Data only for lawful purposes and that under no circumstances will you use this Data to: (1) allow, enable, or otherwise support the transmission of mass unsolicited, commercial advertising or solicitations via e-mail, telephone, or facsimile; or (2) enable high volume, automated, electronic processes repackaging, dissemination or other use of this Data is expressly use electronic processes that are automated and high-volume to access or query the Whois database except as reasonably necessary to register to restrict your access to the Whois database in its sole discretion to ensure reserves the right to modify these terms at any time."
    "The Registry database contains ONLY .COM, .NET, .EDU domains and Registrars. or more information on Whois status codes, please visit https://icann.org/epp"
    "registrar to be reliable, is provided \"as is\" with no guarantee or warranties regarding its accuracy. This information is provided for the sole purpose of assisting you in obtaining information about domain name registration records. Any use of this data for any other purpose is expressly forbidden without the prior written permission of this registrar. By submitting an inquiry, you agree to these terms and limitations of warranty. In particular, you agree not to use this data to allow, enable, or otherwise support the dissemination or collection of this data, in part or in its entirety, for any purpose, such as transmission by e-mail, telephone, postal mail, facsimile or other means of mass unsolicited, commercial advertising or solicitations of any kind, including spam. You further agree not to use this data to enable high volume, automated or robotic electronic processes designed to collect or compile this data for any purpose, including mining this data for your own personal or commercial purposes. Failure to comply with these terms may result in termination of access to the Whois database. These terms may be subject to modification at any time without notice. date of the domain name registrant's agreement with the sponsoring registrar.  Users may consult the sponsoring registrar's Whois database to view the registrar's reported date of expiration for this registration."
"database through the use of electronic processes that are high-volume and automated except as reasonably necessary to register domain names or information purposes only, and to assist persons in obtaining information"
"guarantee its accuracy. By submitting a Whois query, you agree to abide by the following terms of use: You agree that you may use this Data only for lawful purposes and that under no circumstances will you use this Data"
"to: (1) allow, enable, or otherwise support the transmission of mass unsolicited, commercial advertising or solicitations via e-mail, telephone, or facsimile; or (2) enable high volume, automated, electronic processes"
"repackaging, dissemination or other use of this Data is expressly use electronic processes that are automated and high-volume to access or query the Whois database except as reasonably necessary to register"
"to restrict your access to the Whois database in its sole discretion to ensure reserves the right to modify these terms at any time."
"registrar to be reliable, is provided \"as is\" with no guarantee or warranties regarding its accuracy. This information is provided for the sole purpose of assisting you in obtaining information about domain name registration records. Any use of this data for any other purpose is expressly forbidden without the prior written permission of this registrar. By submitting an inquiry, you agree to these terms and limitations of warranty. In particular, you agree not to use this data to allow, enable, or otherwise support the dissemination or collection of this data, in part or in its entirety, for any purpose, such as transmission by e-mail, telephone, postal mail, facsimile or other means of mass unsolicited, commercial advertising or solicitations of any kind, including spam. You further agree not to use this data to enable high volume, automated or robotic electronic processes designed to collect or compile this data for any purpose, including mining this data for your own personal or commercial purposes. Failure to comply with these terms may result in termination of access to the Whois database. These terms may be subject to modification at any time without notice."
)

# Function to filter unwanted lines
filter_whois_output() {
    local whois_output="$1"
    for pattern in "${patterns_to_remove[@]}"; do
        whois_output=$(echo "$whois_output" | grep -v -F "$pattern")
    done
    whois_output=$(echo "$whois_output" | grep -v -E "NOTICE:|TERMS OF USE:|registrar's sponsorship of the domain name registration in the registry is|database through the use of electronic processes that are high-volume and automated|set to expire|VeriSign|submit a Whois query|VeriSign reserves the right")
    echo "$whois_output"
}

# Check if the input is a file or a single domain
if [[ -f "$input" ]]; then
    # Process each domain in the input file
    while IFS= read -r domain; do
        cleaned_domain=$(clean_domain "$domain")
        if [[ -n "$cleaned_domain" ]]; then
            echo "<div class=\"domain\"><h2>$cleaned_domain</h2>" >> "$output_file"
            echo "<pre>" >> "$output_file"
            # Perform whois and filter out unwanted lines
            filtered_output=$(filter_whois_output "$(whois "$cleaned_domain")")
            echo "$filtered_output" >> "$output_file"
            echo "</pre></div>" >> "$output_file"
        fi
    done < "$input"
else
    # Process single domain
    cleaned_domain=$(clean_domain "$input")
    echo "<div class=\"domain\"><h2>$cleaned_domain</h2>" >> "$output_file"
    echo "<pre>" >> "$output_file"
    # Perform whois and filter out unwanted lines
    filtered_output=$(filter_whois_output "$(whois "$cleaned_domain")")
    echo "$filtered_output" >> "$output_file"
    echo "</pre></div>" >> "$output_file"
fi

# End HTML document
echo "</body></html>" >> "$output_file"

# Open the output file in the default browser
if command -v xdg-open &> /dev/null; then
    xdg-open "$output_file"
elif command -v open &> /dev/null; then
    open "$output_file"
else
    echo "HTML file created: $output_file"
fi
