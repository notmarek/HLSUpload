from app.utils import Utils
from app.models import File
from app.encoder import Encoder
from app.encryption import Encryption
from base64 import b64decode, b64encode
from aiohttp import web
import json
import re
import threading
import asyncio
import atexit

class Routes():

    def __init__(self, sqlalchemy_session, base_url='http://127.0.0.1:8080', key: bytes = b"EncryptionAsFuck"):
        self.scoped_session = sqlalchemy_session
        self.session = sqlalchemy_session()
        self.base_url = base_url
        self.loop = asyncio.get_event_loop()
        self.encryption = Encryption(key)
        self.utils = Utils(self.encryption)
        atexit.register(self.cleanup)
        self.being_encoded = []
        self.routes = []
        self.routes += [web.get("/", self.index)]  # Add the index route
        # Add the upload route
        self.routes += [web.post('/upload', self.upload),
                        web.get('/upload', self.upload_page)]
        # Add the ts file route
        self.routes += [web.get('/ts/{b64}', self.ts_file)]
        # Add the m3u8 file route
        self.routes += [web.get('/hls/{b64}', self.get_m3u8)]
        # Add the m3u8 file route
        self.routes += [web.get('/play/{b64}', self.player)]
        # Add the key route
        self.routes += [web.get('/enc/{b64}', self.get_key)]
        # Add the delete route
        self.routes += [web.get('/del/{fid}', self.delete)]
        self.routes += [web.get('/queue', self.queue)]
    
    def cleanup(self):
        self.scoped_session.remove()

    async def queue(self, request):
        data = []
        print(self.being_encoded)
        for x in self.being_encoded:
            try:
                data.append(
                    {'file_name': x.file_name, 'percent': x.percent, 'speed': x.speed, 'size': x.size, 'frame':x.frame, 'frames':x.frames})
            except:
                try:
                    data.append({'file_name':x.file_name, 'percent':x.percent, 'segment':x.segment, 'segments':x.segments})
                except:
                    data.append({'file_name': x.file_name})

        data = json.dumps(data)
        return web.Response(text=data, content_type='application/json')

    async def get_key(self, request):
        base64 = request.match_info.get("b64", None)
        if base64 is None:
            return web.Response(text="Bad request")
        file_id = await self.encryption.decrypt(base64)
        db_entry = self.session.query(File).filter(
            File.file_id == file_id).first()
        return web.Response(text=f"{db_entry.file_key}")

    async def get_m3u8(self, request):
        file_name = request.match_info.get("b64", None)
        if file_name is None:
            return web.Response(text="Bad request")
        base64 = file_name.replace('.m3u8', '')
        file_id = await self.encryption.decrypt(base64)
        with open(f"./hls/{file_id}/master.m3u8", 'r+') as f:
            m3u8 = f.read()
        key_url = await self.utils.gen_key_url(file_id)
        m3u8 = m3u8.replace(",IV=0x00000000000000000000000000000000", '').replace(
            "base_key_url", f"{self.base_url}/enc/{key_url}")
        for x in re.findall("base_urlmaster(.*).ts", m3u8):
            ts_file = await self.utils.generate_ts_url(file_id, x)
            m3u8 = m3u8.replace(
                f"base_urlmaster{x}.ts", f"{self.base_url}/ts/{ts_file}")
        return web.Response(text=m3u8)

    async def ts_file(self, request):
        b64_info = request.match_info.get("b64", None)
        if b64_info is None:
            return web.Response(text='Bad request')
        json_info = json.loads(b64decode(b64_info))
        file = f"./hls/{json_info['file_id']}/master{json_info['part']}.ts"
        return web.FileResponse(file)

    async def upload_page(self, request):
        form = '''<form action="/upload" method="post" accept-charset="utf-8" enctype="multipart/form-data"><label for="file">Video file</label><input id="file" name="file" type="file" value=""/><input type="submit" value="submit"/></form>'''
        return web.Response(text=form, content_type="text/html")

    def bruh(self, encoder, loop: asyncio.AbstractEventLoop):
        asyncio.set_event_loop(loop)
        loop.run_until_complete(encoder.encode())
        loop.close()

    async def upload(self, request):
        reader = await request.multipart()
        field = await reader.next()
        assert field.name == 'file'
        with open(f'./source/{field.filename}', 'wb') as f:
            while True:
                chunk = await field.read_chunk()
                if not chunk:
                    break
                f.write(chunk)
        new_loop = asyncio.new_event_loop()
        threading.Thread(target=self.bruh, args=(Encoder(
            self.scoped_session, field.filename, self.utils, self.being_encoded), new_loop)).start()
        return web.Response(text=f"Encoded {field.filename} to HLS")

    async def player(self, request):
        b64_info = request.match_info.get("b64", None)
        if b64_info is None:
            return web.Response(text='Bad request')
        with open('app/static/player.html', 'r+') as f:
            html = f.read().replace('video_url', f"/hls/{b64_info}")
        return web.Response(text=html, content_type='text/html')

    async def delete(self, request):
        file_id = request.match_info.get("fid", None)
        if file_id is None:
            return web.Response(text='Bad request')
        file = self.session.query(File).filter(File.file_id == file_id).first()
        self.utils.delete_video(file)
        return web.Response(text=f"{file_id} deleted")

    async def index(self, request):
        all_entries = self.session.query(File).filter().all()
        all_entries_string = []
        for x in all_entries:
            all_entries_string.append(f"{x.file_name} - <a href='{self.base_url}/play/{await self.utils.gen_key_url(x.file_id)}.m3u8'>Play</a> <a href='/del/{x.file_id}'>Delete</a></br>")
        text = '\n'.join(x for x in all_entries_string)
        return web.Response(text=text, content_type='text/html')
