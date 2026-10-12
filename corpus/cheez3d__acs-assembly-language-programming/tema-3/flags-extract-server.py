#!/usr/bin/env python3

import aiohttp
import asyncio
import concurrent.futures
import functools
import io

from elftools.elf.elffile import ELFFile
from zipfile import ZipFile

from rc4 import RC4

def extract(zip_bytes):
    zip_file = ZipFile(zip_bytes)

    flags = {}

    for binary_name in zip_file.namelist():
        binary_bytes = io.BytesIO()

        binary_bytes.write(zip_file.read(binary_name))

        elf_file = ELFFile(binary_bytes)

        data = elf_file.get_section_by_name('.data').data()

        encrypted_flag = bytearray(data[8:data.find(b'All done!')-1])
        key = bytes(data[-5:-1])

        keystream = RC4(key)

        flags[binary_name] = ''.join(map(chr, [byte ^ next(keystream) for byte in encrypted_flag]))

    return flags

async def get(username):
    async with aiohttp.ClientSession(headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:72.0) Gecko/20100101 Firefox/72.0'}) as session:
        async with session.post('http://141.85.224.109:5000', data={'username': username}, allow_redirects=False) as redirect:
            if redirect.status != 302:
                return

            async with session.get(redirect.headers['Location'], cookies=redirect.cookies) as homework:
                if homework.status != 200 or homework.headers['Content-Type'] != 'application/zip':
                    return

                zip_bytes = io.BytesIO()

                while True:
                    chunk = await homework.content.read(1024)
                    if not chunk:
                        break

                    zip_bytes.write(chunk)

                loop = asyncio.get_running_loop()

                with concurrent.futures.ThreadPoolExecutor() as pool:
                    flags = await loop.run_in_executor(pool, functools.partial(extract, zip_bytes))

                    return flags
