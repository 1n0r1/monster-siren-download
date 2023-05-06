import os
import requests
from tqdm import tqdm
import pylrc
import json

from PIL import Image
from multiprocessing import Pool, Manager
from mutagen.easyid3 import EasyID3
from mutagen.id3 import APIC, SYLT, Encoding, ID3
from mutagen.flac import Picture, FLAC
from pydub import AudioSegment


def make_valid(filename):
    # Make a filename valid in different OSs
    f = filename.replace(':', '_')
    f = f.replace('/', '_')
    f = f.replace('<', '_')
    f = f.replace('>', '_')
    f = f.replace('\'', '_')
    f = f.replace('\\', '_')
    f = f.replace('|', '_')
    f = f.replace('?', '_')
    f = f.replace('*', '_')
    f = f.replace(' ', '_')
    return f


def lyric_file_to_text(filename):
    lrc_file = open(filename, 'r', encoding='utf-8')
    lrc_string = ''.join(lrc_file.readlines())
    lrc_file.close()
    subs = pylrc.parse(lrc_string)
    ret = []
    for sub in subs:
        time = int(sub.time * 1000)
        text = sub.text
        ret.append((text, time))
    return ret

def update_downloaded_albums(queue, directory):
    while 1:
        album_name = queue.get()
        try:
            with open(directory + 'completed_albums.json', 'r', encoding='utf8') as f:
                completed_albums = json.load(f)
        except:
            completed_albums = []
        completed_albums.append(album_name)
        with open(directory + 'completed_albums.json', 'w+', encoding='utf8') as f:
            json.dump(completed_albums, f)


def fill_metadata(filename, filetype, album, title, albumartist, artist, tracknumber, albumcover, songlyricpath):
    if filetype == '.mp3':
        file =  EasyID3(filename)
    else:
        file = FLAC(filename)

    file['album'] = album
    file['title'] = title
    file['albumartist'] = ''.join(albumartist)
    file['artist'] = ''.join(artist)
    file['tracknumber'] = str(tracknumber + 1)
    file.save()

    if filetype == '.mp3':
        file = ID3(filename)
        file.add(APIC(mime='image/png',type=3,desc='Cover',data=open(albumcover,'rb').read()))
        # Read and add lyrics
        if (songlyricpath != None):
            sylt = lyric_file_to_text(songlyricpath)
            file.setall('SYLT', [SYLT(encoding=Encoding.UTF8, lang='eng', format=2, type=1, text=sylt)])
        file.save()
    else:
        image = Picture()
        image.type = 3
        image.desc = 'Cover'
        image.mime = 'image/png'
        with open(albumcover,'rb') as f:
            image.data = f.read()
        with Image.open(albumcover) as imagePil:
            image.width, image.height = imagePil.size
            image.depth = 24
        file.add_picture(image)
        # Read and add lyrics
        if (songlyricpath != None):
            musiclrc = open(songlyricpath, 'r', encoding='utf-8').read()
            file['lyrics'] = musiclrc
        file.save()

    return 


def download_song(session, directory, name, url):
    source = session.get(url, stream=True)
    filename = directory + '/' + make_valid(name)
    filetype = ''

    if source.headers['content-type'] == 'audio/mpeg':
        filename += '.mp3'
        filetype = '.mp3'
    else:
        filename += '.wav'

    # Download song
    total = int(source.headers.get('content-length', 0))
    with open(filename, 'w+b') as f, tqdm(
        desc=name,
        total=total,
        unit='iB',
        unit_scale=True,
        unit_divisor=1024,
    ) as bar:
        for data in source.iter_content(chunk_size = 1024):
            size = f.write(data)
            bar.update(size)

    # If file is .wav then export to .flac
    if source.headers['content-type'] != 'audio/mpeg':
        AudioSegment.from_wav(filename).export(directory + '/' + make_valid(name) + '.flac', format='flac')
        os.remove(filename)
        filename = directory + '/' + make_valid(name) + '.flac'
        filetype = '.flac'

    return filename, filetype


def download_album( args):
    directory = args['directory']
    session = args['session']
    queue = args['queue']

    album_cid = args['cid']
    album_name = args['name']
    album_coverUrl = args['coverUrl']
    album_artistes = args['artistes']
    album_url = 'https://monster-siren.hypergryph.com/api/album/' + album_cid + '/detail'

    try:
        with open(directory + 'completed_albums.json', 'r', encoding='utf8') as f:
            completed_albums = json.load(f)
    except:
        completed_albums = []

    if album_name in completed_albums:
        # If album is completed then skip
        print(f'Skipping downloaded album {album_name}')
        return

    try:
        os.mkdir(directory + make_valid(album_name))
    except:
        pass

    # Download album art
    with open(directory + make_valid(album_name) + '/cover.jpg', 'w+b') as f:
        f.write(session.get(album_coverUrl).content)

    # Change album art from .jpg to .png
    cover = Image.open(directory + make_valid(album_name) + '/cover.jpg')
    cover.save(directory + make_valid(album_name) + '/cover.png')
    os.remove(directory + make_valid(album_name) + '/cover.jpg')


    songs = session.get(album_url, headers={'Accept': 'application/json'}).json()['data']['songs']
    for song_track_number, song in enumerate(songs):
        # Get song details
        song_cid = song['cid']
        song_name = song['name']
        song_artists = song['artistes']
        song_url = 'https://monster-siren.hypergryph.com/api/song/' + song_cid
        song_detail = session.get(song_url, headers={'Accept': 'application/json'}).json()['data']
        song_lyricUrl = song_detail['lyricUrl']
        song_sourceUrl = song_detail['sourceUrl']

        # Download lyric
        if (song_lyricUrl != None):
            songlyricpath = directory + make_valid(album_name) + '/' + make_valid(song_name) + '.lrc'
            with open(songlyricpath, 'w+b') as f:
                f.write(session.get(song_lyricUrl).content)
        else:
            songlyricpath = None

        # Download song and fill out metadata
        filename, filetype = download_song(session=session, directory=directory + make_valid(album_name), name=song_name, url=song_sourceUrl)
        fill_metadata(filename=filename,
                        filetype=filetype,
                        album=album_name,
                        title=song_name,
                        albumartist=album_artistes,
                        artist=song_artists,
                        tracknumber=song_track_number,
                        albumcover=directory + make_valid(album_name) + '/cover.png',
                        songlyricpath=songlyricpath)
    
    # Mark album as finished
    queue.put(album_name)

    return


def main():
    directory = './MonsterSiren/'
    session = requests.Session()
    manager = Manager()
    queue = manager.Queue()

    try:
        os.mkdir(directory)
    except:
        pass

    
    # Get all albums
    albums = session.get('https://monster-siren.hypergryph.com/api/albums', headers={'Accept': 'application/json'}).json()['data']
    for album in albums:
        album['directory'] = directory
        album['session'] = session
        album['queue'] = queue


    with Pool(maxtasksperchild=1) as pool:
        pool.apply_async(update_downloaded_albums, (queue, directory))
        pool.map(download_album, albums)
        queue.put('kill')
    
    return



if __name__ == '__main__':
    main()