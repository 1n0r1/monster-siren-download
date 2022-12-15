Tested on Ubuntu and Python 3


A simple script to download all your favorite Arknights OSTs from monster-siren.hypergryph.com

Download all songs, albums and fill out metadata, album, cover art, artists and even lyrics

### Note:

The API offers .mp3 and .wav, but the program convert .wav to .mp3, which is lossy. If you care about the quality, I suggest convert .wav to .flac and fill metadata on .flac instead (since .wav can't do metadata). .flac use Vorbis instead of ID3 so filling metadata is a bit different.


### Requirements:

Python

ffmpeg

```pip install -r requirements.txt```

### Runs:

```python3 main.py```


![image](https://user-images.githubusercontent.com/80285371/207703442-a96488bc-5642-4d7b-92da-f0ac976e944b.png)
![image](https://user-images.githubusercontent.com/80285371/207703484-2271b5a1-7928-401d-9bed-a5e4feeec4d0.png)
