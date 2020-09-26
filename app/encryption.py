from base64 import b64decode, b64encode
from Crypto.Cipher import AES
from urllib.parse import quote
from Crypto.Util.Padding import pad, unpad

class Encryption():
    def __init__(self, key:bytes, iv:bytes = b'0000000000000000'):
        self.__key = key
        self.__iv = iv

    async def decrypt(self, base64data):
        cipher = AES.new(self.__key, AES.MODE_CBC, self.__iv) 
        return unpad(cipher.decrypt(b64decode(base64data)), AES.block_size).decode('utf8')
    
    async def encrypt(self, string):
        data = bytes(string, "utf8")
        cipher = AES.new(self.__key, AES.MODE_CBC, self.__iv) 
        return cipher.encrypt(pad(data, AES.block_size))