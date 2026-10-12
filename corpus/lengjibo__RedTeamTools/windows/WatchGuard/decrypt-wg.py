from typing import Optional
from Crypto.Cipher import AES
import binascii
import re
import struct

def group_by_count(byte_array: bytes, n: int) -> list[bytes]:
    
    num_groups = len(byte_array) // n
    output = []
    for i in range(num_groups):
        output.append(byte_array[i * n:(i + 1) * n])
    return output

def decrypt_watchguard_psk(encrypted_psk: str) -> str:

    key_encryption_key = bytes([
        29, 3, 245, 130, 135, 152, 43, 199,
        1, 34, 115, 148, 228, 152, 222, 35
    ])  # 1d03f58287982bc701227394e498de23

 
    encrypted_psk = re.sub(r'\s|(</?psk>)|\+', '', encrypted_psk)
    

    try:
        arrby = binascii.unhexlify(encrypted_psk)
    except binascii.Error:
        raise ValueError("need hex")

   
    if len(arrby) % 8 != 0:
        raise ValueError("error")
    c = group_by_count(arrby, 8)
    
   
    a = c[0]  
    r = c[1:]
    block_n = len(r) 

  
    for j in range(5, -1, -1):  # j=5..0
        for i in range(block_n - 1, -1, -1):  # i=n-1..0
            t = block_n * j + i + 1  # t = n*j + i + 1

           
            a2 = bytearray(a)
            a2.reverse()  
            a_int = struct.unpack('<Q', bytes(a2))[0]  
            a_int ^= t  
            a2 = bytearray(struct.pack('<Q', a_int))  
            a2.reverse()  
            a = bytes(a2)

           
            cipher = AES.new(key_encryption_key, AES.MODE_ECB)
            a_concat_ri = a + r[i]  
            b = cipher.decrypt(a_concat_ri)

        
            a = b[:8]
            r[i] = b[8:]


    try:
        result = ''.join(chr(b) for block in r for b in block if 32 <= b <= 126)
        return result
    except UnicodeEncodeError:
        raise ValueError("error")


if __name__ == "__main__":
    encrypted_psk = ""
    try:
        decrypted = decrypt_watchguard_psk(encrypted_psk)
        print("decrypt PSK:", decrypted)
    except ValueError as e:
        print("error:", e)
