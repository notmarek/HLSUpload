import random
import string
from urllib.parse import quote
import shutil
from app import Session
from base64 import b64decode, b64encode

class Utils():
    def __init__(self, encryption):
        self.__encryption = encryption

    def delete_video(self, file):
        
        shutil.rmtree(f"hls/{file.file_id}")
        session = Session()
        session.delete(file)
        session.commit()
        Session.remove()

    def generate_key(self):
        characters = string.ascii_lowercase + string.ascii_uppercase + string.digits
        return "".join(random.choice(characters) for i in range(16))

    async def gen_key_url(self, file_id):
        file_id = f'{file_id}'
        encrypted = await self.__encryption.encrypt(file_id)
        return quote(b64encode(encrypted).decode('utf8')).replace('/', '%2F')

    def generate_file_id(self):
        return random.randint(0, 99999)

    async def generate_ts_url(self, file_id, part):
        json_encoded = f'{{"file_id":{file_id},"part":{part}}}'
        return quote(b64encode(bytes(json_encoded, "utf8")).decode('utf8')).replace('/', '%2F')