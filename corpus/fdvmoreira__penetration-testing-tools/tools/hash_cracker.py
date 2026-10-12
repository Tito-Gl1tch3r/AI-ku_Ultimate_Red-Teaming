#!/usr/bin/python3

"""
Hash Cracker
Crack hashes with wordlists. Algorithms supported: [md5, sha256]

by Flavio Moreira
"""

import argparse
import pyfiglet
import hashlib
import enum

# setup banner
banner = pyfiglet.figlet_format("Hash Cracker")
print(banner)

# arguments handling
parser = argparse.ArgumentParser(prog="Hash Cracker", description="Crack MD5 and sha256 hashes with a wordlist", epilog="by Flavio Moreira")
parser.add_argument("--wordlist", "-w", required=True, type=str, help="Wordlist to use for cracking the hash")
parser.add_argument("--hash", "--dump", "-d", type=str, help="Hash to be cracked")
parser.add_argument("--algorithm", "-a", type=str, choices={"MD5", "SHA256"}, default="MD5", help="Hashing algorithm to be used.")

# List supported Algorithms
Algorithm = enum.Enum(value="Algorithm", names=["MD5", "SHA256"])

#Hash Cracker
class Cracker:
    pass

cracker = Cracker()
parser.parse_args(namespace=cracker)

wordlist = cracker.wordlist
input_hash = cracker.hash
algorithm = cracker.algorithm

# prompt the user to enter the hash if it has not been provided
if not input_hash:
    input_hash = str(input("Hash: "))

# check the digest of each word in the list
try:
    print("Loading ...",end="\r")
    with open(wordlist) as file:
        lines = file.readlines()
        found = False

        print("Hashing ...")
        for line in lines:
            new_hash = None

            match algorithm:
                case Algorithm.MD5.name:
                    new_hash = hashlib.md5(line.strip().encode()).hexdigest()
                case Algorithm.SHA256.name:
                    new_hash = hashlib.sha256(line.strip().encode()).hexdigest()
                case _:
                    new_hash = None

            if new_hash == input_hash:
                print(f"SUCCESS\n{input_hash} => {line}")
                found = True
                break
        
        if not found:
            print(f"Hash {input_hash} NOT found")

except Exception as ex:
    print(f"Something  went wrong\n{ex}")

