import os
import requests
from tqdm import tqdm
import pylrc
import shutil

from mutagen.easyid3 import EasyID3
from mutagen.id3 import APIC, SYLT, Encoding, ID3
from pydub import AudioSegment
from PIL import Image




def make_valid(filename):
    f = filename.replace(":", "_")
    f = f.replace("/", "_")
    f = f.replace("<", "_")
    f = f.replace(">", "_")
    f = f.replace("\"", "_")
    f = f.replace("\\", "_")
    f = f.replace("|", "_")
    f = f.replace("?", "_")
    f = f.replace("*", "_")
    return f

def lyric_file_to_text(filename):
    lrc_file = open(filename, 'r')
    lrc_string = ''.join(lrc_file.readlines())
    lrc_file.close()

    subs = pylrc.parse(lrc_string)
    
    ret = []
    for sub in subs:
        time = int(sub.time * 1000)
        text = sub.text
        ret.append((text, time))

    return ret


directory = './MonsterSiren/'
shutil.rmtree(directory)
try:
    os.mkdir(directory)
except:
    pass

session = requests.Session()
headers = {'Accept': 'application/json'}

# Get all albums
albums = session.get('https://monster-siren.hypergryph.com/api/albums', headers=headers).json()['data']
for album in albums:
    album_cid = album['cid']
    album_name = album['name']
    album_coverUrl = album['coverUrl']
    album_artistes = album['artistes']
    album_url = 'https://monster-siren.hypergryph.com/api/album/' + album_cid + '/detail'

    try:
        os.mkdir(directory + '/' + album_name)
    except:
        pass

    # Download album art
    with open(directory + '/' + album_name + '/cover.jpg', 'w+b') as f:
        f.write(session.get(album_coverUrl).content)

    # Change album art from .jpg to .png
    cover = Image.open(directory + '/' + album_name + '/cover.jpg')
    cover.save(directory + '/' + album_name + '/cover.png')
    os.remove(directory + '/' + album_name + '/cover.jpg')

    songs = session.get(album_url, headers=headers).json()['data']['songs']
    for song_track_number, song in enumerate(songs):
        song_cid = song['cid']
        song_name = song['name']
        song_artists = song['artistes']
        song_url = 'https://monster-siren.hypergryph.com/api/song/' + song_cid

        # Get song detail
        song_detail = session.get(song_url, headers=headers).json()['data']
        song_lyricUrl = song_detail['lyricUrl']
        song_sourceUrl = song_detail['sourceUrl']
        
        source = session.get(song_sourceUrl, stream=True)

        filename = directory + album_name + '/' + make_valid(song_name)
        if source.headers['content-type'] == 'audio/mpeg':
            filename += '.mp3'
        else:
            filename += '.wav'

        # Download song
        total = int(source.headers.get('content-length', 0))
        with open(filename, "w+b") as f, tqdm(
            desc=song_name,
            total=total,
            unit='iB',
            unit_scale=True,
            unit_divisor=1024,
        ) as bar:
            for data in source.iter_content(chunk_size = 1024):
                size = f.write(data)
                bar.update(size)
        if source.headers['content-type'] != 'audio/mpeg':
            # If file is .wav then export to .mp3
            AudioSegment.from_wav(filename).export(directory + album_name + '/' + make_valid(song_name) + '.mp3', format='mp3')
            os.remove(filename)
            filename = directory + album_name + '/' + make_valid(song_name) + '.mp3'


        # Download lyric
        if (song_lyricUrl != None):
            with open(directory + '/' + album_name + '/' + make_valid(song_name) + '.lrc', 'w+b') as f:
                f.write(session.get(song_lyricUrl).content)


        # Write metadata
        file =  EasyID3(filename)
        file['album'] = album_name
        file['title'] = song_name
        file['albumartist'] = ''.join(album_artistes)
        file['artist'] = ''.join(song_artists)
        file['tracknumber'] = str(song_track_number + 1)
        file.save()
        file = ID3(filename)
        file.add(APIC(mime='image/jpeg',type=3,desc=u'Cover',data=open(directory + album_name + '/cover.png','rb').read()))
        # Read and add lyrics
        if (song_lyricUrl != None):
            sylt = lyric_file_to_text(directory + '/' + album_name + '/' + make_valid(song_name) + '.lrc')
            file.setall("SYLT", [SYLT(encoding=Encoding.UTF8, lang='eng', format=2, type=1, text=sylt)])

        file.save()
    




