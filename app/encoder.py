
from app.models import File
from subprocess import Popen, PIPE, run, DEVNULL
import os
import copy
import re
import math
from ffmpeg_progress import start
import pexpect
class EncodingMP4():
    def __init__(self, file_name):
        self.file_name = file_name
    
    def update(self, data):
        self.frames = data.get('frames', None)
        self.frame = data.get('frame', None)
        self.fps = data.get('fps', None)
        self.size = data.get('size', None)
        self.time = data.get('time', None)
        self.bitrate = data.get('bitrate', None)
        self.speed = data.get('speed', None)
        self.percent = data.get('percent', None)

    def __repr__(self):
        try:
            return f'{self.percent:.2f} - {self.frame}/{self.frames} frames @ {self.fps} fps or {self.speed} speed, bitrate: {self.bitrate}, current time = {self.time}, current size = {self.size}'
        except Exception as e:
            print(e)
            return f"{self.file_name}"

class EncodingHLS():
    def __init__(self, file_name):
        self.file_name = file_name
    
    def update(self, data):
        self.segments = data.get('segments', None)
        self.segment = data.get('segment', None)
        self.percent = data.get('percent', None)

    def __repr__(self):
        try:
            return f'{self.percent:.2f} - {self.segment}/{self.segments}'
        except Exception as e:
            print(e)
            return f"{self.file_name}"

class Encoder():
    def __init__(self, sqlalchemy_session, file, utils, being_encoded):
        self.scoped_session = sqlalchemy_session
        self.__session = sqlalchemy_session()
        self.being_encoded = being_encoded
   
        self.__utils = utils
        self.__key = self.__utils.generate_key()
        self.file_id = self.__utils.generate_file_id()
        self.file_name, self.file_extension = file.rsplit(".", 1)
        self.encoding = EncodingMP4(self.file_name)
        self.being_encoded.append(self.encoding)
        for x in self.being_encoded:
            if x == self.encoding:
                self.encoding = x
        self.vstat = "vstat.log"
        id_db_entry = self.__session.query(File).filter(
            File.file_id == self.file_id).first()
        name_db_entry = self.__session.query(File).filter(
            File.file_name == self.file_name).first()
        self.scoped_session.remove()
        if name_db_entry is not None:
            raise Exception(f"{self.file_name} already exists in the DB.")
        if id_db_entry is not None:
            self.__init__(file)

    def on_message_handler(self, percent: float, fr_cnt: int,  total_frames: int, elapsed: float):
        print(percent, fr_cnt, total_frames, elapsed)
    def ffmpeg_hls(self, ffmpeg_cmd):
        ffmpeg = Popen(ffmpeg_cmd, stderr=PIPE, universal_newlines=True)
        
        for i, x in enumerate(self.being_encoded):
            if x == self.encoding:
                self.being_encoded[i] = self.encoding = EncodingHLS(self.file_name)
        duration = ''
        segments = 0
        for line in iter(ffmpeg.stderr.readline, b''):
            try:
                line = line.rstrip()

                if line == '':
                    break
                # print(line)     
            
                if duration == '':
                    try:
                        if 'duration' in line.lower():
                            duration = line.split(',',1)[0]
                            duration = duration.replace('  Duration: ','')
                            print(duration)
                            duration = duration.split('.')[0]
                            duration_secs = 0
                            for i, x in enumerate(duration.split(':')[::-1]):
                                if i == 0:
                                    b = 1
                                else:
                                    b = i*60
                                duration_secs += (b*int(x))
                            segments = math.ceil(duration_secs / 10.4)
                    except:
                        pass
                try:
                    if 'hls' in line:
                        result = re.search('master(.*)\.ts', line)
                        segment = int(result.group(1)) + 1
                        data = { "segments": segments,
                                 "segment": segment,
                                 "percent": segment / (segments / 100)}
                        self.encoding.update(data)
                        print(self.encoding.__dict__)
                        # print(f'{percent:.2f} - {frame}/{frames} frames @ {fps} fps or {speed} speed, bitrate: {bitrate}, current time = {time}, current size = {size}')
                except:
                    pass
            except:
                pass
        return 'Bruh'

    def ffmpeg_mp4(self, ffmpeg_cmd):
        ffmpeg = Popen(ffmpeg_cmd, stderr=PIPE, universal_newlines=True)
        frames = ''
        for line in iter(ffmpeg.stderr.readline, b''):
            try:
                line = line.rstrip()
                if line == '':
                    break
                # print(line)                
                if frames == '':
                    try:
                        
                        thing, value = line.split(': ')
                        if 'NUMBER_OF_FRAMES' in thing:
                            frames = int(value.replace(' ', ''))
                    except:
                        pass
                try:
                    if 'frame=' in line:
                        result = re.search('frame\=(.*) fps\=(.*) q\=(.*) size\=(.*) time\=(.*) bitrate\=(.*) speed\=(.*)', line) or re.search('frame\=(.*) fps\=(.*) q\=(.*) Lsize\=(.*) time\=(.*) bitrate\=(.*) speed\=(.*)', line)
                        frame = int(result.group(1).replace(' ', ''))
                        data = { "frames": frames,
                            "frame": frame,
                        "fps": int(result.group(2).replace(' ', '')),
                        "size": result.group(4).replace(' ', ''),
                        "time": result.group(5).replace(' ', ''),
                        "bitrate": result.group(6).replace(' ', ''),
                        "speed": result.group(7).replace(' ', ''),
                        "percent": float(frame / (frames / 100))}
                        self.encoding.update(data)
                        
                        # print(f'{percent:.2f} - {frame}/{frames} frames @ {fps} fps or {speed} speed, bitrate: {bitrate}, current time = {time}, current size = {size}')
                except:
                    pass
            except:
                pass
        return 'Bruh'

    async def to_mp4(self):
        ffmpeg_cmd = f"ffmpeg -i \"source/{self.file_name}.{self.file_extension}\" -acodec copy -preset fast -vcodec hevc_nvenc -vf \"subtitles=\'source/{self.file_name}.{self.file_extension}\'\" \"source/{self.file_name}.mp4\""
        
        self.ffmpeg_mp4(ffmpeg_cmd)
        # start(f"source/{self.file_name}.{self.file_extension}",f"source/{self.file_name}.mp4",self.ffmpeg_mp4_callback, on_message=self.on_message_handler, on_done=lambda: print('Done!'), wait_time=1)
        os.remove(f"./source/{self.file_name}.{self.file_extension}")
        # os.remove(f"./source/{self.file_name}.mp4") # remove this later ok?
        self.file_extension = 'mp4'

    async def to_hls(self):
        if self.file_extension.lower() != 'mp4':
            raise Exception("File isn't MP4.")
        os.mkdir(f"./hls/{self.file_id}")
        
        ffmpeg_cmd = f"ffmpeg -i \"source/{self.file_name}.mp4\" -hls_playlist_type vod -hls_enc 1 -hls_enc_key {self.__key} -hls_enc_key_url base_key_url -hls_base_url base_url -codec: copy -start_number 0 -hls_time 10 -hls_list_size 0 -f hls hls/{self.file_id}/master.m3u8"
        self.ffmpeg_hls(ffmpeg_cmd)
        os.remove('base_key_url')
        os.remove(f"./source/{self.file_name}.mp4")

    async def add_to_db(self):
        file = File(file_id=self.file_id,
                    file_name=self.file_name, file_key=self.__key)
        self.__session = self.scoped_session()
        self.__session.add(file)
        self.__session.commit()
        self.scoped_session.remove()

    async def encode(self):
        if self.file_extension.lower() != 'mp4':
            print('bruh')
            await self.to_mp4()
        await self.to_hls()
        await self.add_to_db()
        print('bye')