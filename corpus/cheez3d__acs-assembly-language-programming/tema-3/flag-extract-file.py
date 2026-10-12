#!/usr/bin/env python3

import sys

from elftools.elf.elffile import ELFFile

from rc4 import RC4

def flag_extract(path):
    with open(path, 'rb') as file:
        elf_file = ELFFile(file)

        data = elf_file.get_section_by_name('.data').data()

        flag = bytearray(data[8 : data.find(b'All done!') - 1])
        key = bytes(data[-5 : -1])

    return flag, key

def flag_decrypt(flag, key):
    keystream = RC4(key)

    return ''.join(map(chr, [b ^ next(keystream) for b in flag]))

print(flag_decrypt(*flag_extract(sys.argv[1])))
