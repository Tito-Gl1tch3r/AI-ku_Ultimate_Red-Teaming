#!/bin/bash

# Chrome Native Messaging Host for macOS - Pure Bash Implementation
# Ports the functionality from the .NET NativeAppHost

# Function to write length as 4-byte little-endian integer
write_length() {
    local length=$1
    printf "\\$(printf '%03o' $((length & 0xFF)))"
    printf "\\$(printf '%03o' $(((length >> 8) & 0xFF)))"
    printf "\\$(printf '%03o' $(((length >> 16) & 0xFF)))"
    printf "\\$(printf '%03o' $(((length >> 24) & 0xFF)))"
}

# Function to parse JSON message and extract the "message" field
parse_json_message() {
    local json_input="$1"
    
    # Use osascript to parse JSON (equivalent to C# JSON parsing)
    # Escape quotes and backslashes for JavaScript string literal
    local escaped_input="${json_input//\\/\\\\}"  # Escape backslashes first
    escaped_input="${escaped_input//\"/\\\"}"     # Then escape quotes
    
    local message
    message=$(osascript -l JavaScript -e "
        const input = \"$escaped_input\";
        try {
            const obj = JSON.parse(input);
            if (obj.message) {
                console.log(obj.message);
            } else {
                console.log('ERROR: No message field found');
            }
        } catch (e) {
            console.log('ERROR: Invalid JSON - ' + e.message);
        }
    " 2>&1)
    
    echo "$message"
}

# Function to execute command and return output
execute_command() {
    local message="$1"
    
    # Check if message contains pipe separator (like C# code)
    if [[ "$message" != *"|"* ]]; then
        echo "Message \"$message\" was not correctly formatted"
        return
    fi
    
    # Split command and arguments on first pipe (like C# Split('|'))
    local command="${message%%|*}"
    local args="${message#*|}"
    
    # Execute command with arguments and capture output
    local output
    if command -v "$command" >/dev/null 2>&1; then
        # Execute command and capture both stdout and stderr
        output=$(eval "$command $args" 2>&1)
    else
        output="An Error happened: Command '$command' not found"
    fi
    
    echo "$output"
}

# Function to encode output and send response
send_response() {
    local output="$1"
    
    # Base64 encode the output (like C# Convert.ToBase64String)
    local encoded_data
    encoded_data=$(printf '%s' "$output" | base64)
    
    # Create JSON response (like C# string.Format)
    local response="{\"data\":\"$encoded_data\"}"
    
    # Calculate length
    local length=${#response}
    
    # Write 4-byte length prefix + response
    write_length "$length"
    printf '%s' "$response"
}

# Main - Process SINGLE message and exit
main() {
    # Read message length (4 bytes, little-endian)
    local bytes
    bytes=$(dd bs=4 count=1 2>/dev/null | od -An -tu1)
    
    # Check if we got any data
    if [ -z "$bytes" ]; then
        exit 0
    fi
    
    # Parse the 4 bytes from od output
    set -- $bytes
    local byte1=${1:-0}
    local byte2=${2:-0}
    local byte3=${3:-0}
    local byte4=${4:-0}
    
    # Convert little-endian to integer
    local message_length=$(( byte1 + (byte2 << 8) + (byte3 << 16) + (byte4 << 24) ))
    
    # Check for invalid length
    if [ "$message_length" -le 0 ] || [ "$message_length" -gt 1048576 ]; then
        exit 1
    fi
    
    # Read the actual message
    local raw_message
    raw_message=$(dd bs="$message_length" count=1 2>/dev/null)
    
    if [ -z "$raw_message" ]; then
        exit 1
    fi
    
    # Parse JSON to extract the message field
    local parsed_message
    parsed_message=$(parse_json_message "$raw_message")
    
    if [[ "$parsed_message" == ERROR:* ]]; then
        send_response "$parsed_message"
        exit 1
    fi
    
    # Execute the command and get output
    local command_output
    command_output=$(execute_command "$parsed_message")
    
    # Send response back
    send_response "$command_output"
    
    # IMPORTANT: Exit immediately after sending response
    exit 0
}

# Trap signals to ensure clean exit
trap 'exit 0' SIGTERM SIGINT SIGHUP

# Run main function and ensure exit
main
exit 0
