import os
import itertools
import requests
from tqdm import tqdm
import pylrc
import json

from PIL import Image
from multiprocessing import Pool, Manager
import multiprocessing
from mutagen.easyid3 import EasyID3
from mutagen.id3 import APIC, SYLT, Encoding, ID3
from mutagen.flac import Picture, FLAC
from pydub import AudioSegment

#batch size of multiprocessing. reduce batch number for quicker termination when GUI is closed. 
#But overhead time is massively increased. adjust this value to better suit your need. bigger number = faster = slower close time
batch_size = 5
progressTracker = 0

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
            with open(directory + '\\' + 'completed_albums.json', 'r', encoding='utf8') as f:
                completed_albums = json.load(f)
        except:
            completed_albums = []
        completed_albums.append(album_name)
        with open(directory + '\\' + 'completed_albums.json', 'w+', encoding='utf8') as f:
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

#To implement select download location, changed some directory naming.
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
        with open(directory + '\\' + 'completed_albums.json', 'r', encoding='utf8') as f:
            completed_albums = json.load(f)
    except:
        completed_albums = []

    if album_name in completed_albums:
        # If album is completed then skip
        print(f'Skipping downloaded album {album_name}')
        return

    download2 = directory + '\\' + make_valid(album_name)
    try:
        os.mkdir(download2)
    except:
        pass

    # Download album art
    with open(download2 + '/cover.jpg', 'w+b') as f:
        f.write(session.get(album_coverUrl).content)

    # Change album art from .jpg to .png
    cover = Image.open(download2 + '/cover.jpg')
    cover.save(download2 + '/cover.png')
    os.remove(download2 + '/cover.jpg')


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
            songlyricpath = download2 + '/' + make_valid(song_name) + '.lrc'
            with open(songlyricpath, 'w+b') as f:
                f.write(session.get(song_lyricUrl).content)
        else:
            songlyricpath = None

        # Download song and fill out metadata
        filename, filetype = download_song(session=session, directory=download2, name=song_name, url=song_sourceUrl )
        fill_metadata(filename=filename,
                        filetype=filetype,
                        album=album_name,
                        title=song_name,
                        albumartist=album_artistes,
                        artist=song_artists,
                        tracknumber=song_track_number,
                        albumcover=download2 + '/cover.png',
                        songlyricpath=songlyricpath)
    
    # Mark album as finished
    queue.put(album_name)
    return

def main(dir, progressbar, indicator):
    global batch_size
    session = requests.Session()
    manager = Manager()
    queue = manager.Queue()

    try:
        os.mkdir(dir)
    except:
        pass

    # Get all albums
    albums = session.get('https://monster-siren.hypergryph.com/api/albums', headers={'Accept': 'application/json'}).json()['data']
    for album in albums:
        album['directory'] = dir
        album['session'] = session
        album['queue'] = queue
    
    #changed from map to imap_unsorted for better response of GUI progress bar.
    with Pool(maxtasksperchild=1) as pool:
        pool.apply_async(update_downloaded_albums, (queue, dir))
        albums_iterator = iter(albums)
        for each in albums_iterator:
            result = pool.imap_unordered(download_album, itertools.islice(albums_iterator, batch_size))
            try:
                for _ in result:
                    updateBar(progressbar, len(albums))
            except KeyboardInterrupt:
                queue.put('kill')
                pool.terminate()
                pool.join()
                break
            except Exception as e:
                print('WARNING', e)
                queue.put('kill')
                pool.terminate()
                pool.join()
                break
            
        finish(progressbar, indicator)
        queue.put('kill')

    return

#update GUI progress bar
def updateBar(widget, step):
    try:
        step = 100/step
        global progressTracker
        progressTracker += step
        #now = int(-(-(widget.amountusedvar.get() + step)//1))#round up without using math.
        widget.configure(amountused = int(progressTracker))
    except:
        pass
    return

#update GUI to finish
def finish(bar, indicator):
    try:
        bar.configure(subtext = 'Finish!', bootstyle = 'success', subtextstyle = 'success', amountused = 100)
        indicator.grid_forget()
        global progressTracker
        progressTracker = 0
    except:
        pass
    return

if __name__ == '__main__':
    multiprocessing.freeze_support()
    main('./', None, None)