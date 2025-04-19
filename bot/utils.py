import yt_dlp as youtube_dl
from spotipy import Spotify
from spotipy.oauth2 import SpotifyClientCredentials
from .config import SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET

# Configuración de Spotify
sp = Spotify(auth_manager=SpotifyClientCredentials(
    client_id=SPOTIFY_CLIENT_ID,
    client_secret=SPOTIFY_CLIENT_SECRET
))

def search_spotify(query):
    try:
        results = sp.search(q=query, type='track', limit=1)
        if results['tracks']['items']:
            track = results['tracks']['items'][0]
            track_name = f"{track['name']} {track['artists'][0]['name']}"
            album_image = track['album']['images'][0]['url'] if track['album']['images'] else None
            duration_ms = track['duration_ms']
            duration_sec = duration_ms // 1000
            return track_name, album_image, duration_sec
        return None, None, 0
    except Exception as e:
        print(f"Error al buscar en Spotify: {e}")
        return None, None, 0

def get_spotify_track_info(url):
    try:
        track_info = sp.track(url)
        track_name = f"{track_info['name']} {track_info['artists'][0]['name']}"
        album_image = track_info['album']['images'][0]['url'] if track_info['album']['images'] else None
        duration_ms = track_info['duration_ms']
        duration_sec = duration_ms // 1000
        return track_name, album_image, duration_sec
    except Exception as e:
        print(f"Error al obtener info de Spotify: {e}")
        return None, None, 0

def get_youtube_info(url_or_query, is_url=False):
    ydl_opts = {
        'format': 'bestaudio[ext=webm]/bestaudio[ext=m4a]/bestaudio/best',
        'quiet': True,
        'noplaylist': True,
        'default_search': 'ytsearch' if not is_url else None,
        'extract_flat': False,
        'no_warnings': True,
        'ignoreerrors': True,
        'force_generic_extractor': True,
    }
    try:
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            if is_url:
                info = ydl.extract_info(url_or_query, download=False)
            else:
                info = ydl.extract_info(f"ytsearch:{url_or_query}", download=False)
                if 'entries' in info and info['entries']:
                    info = info['entries'][0]
            if not info:
                return None, None, None, 0, None, None
            print(f"Formato seleccionado para {url_or_query}: {info.get('url')}")
            return info.get('url'), info.get('title'), info.get('thumbnail'), info.get('duration', 0), f"https://www.youtube.com/watch?v={info.get('id')}", info.get('uploader', 'Desconocido')
    except Exception as e:
        print(f"Error en yt_dlp: {str(e)}")
        return None, None, None, 0, None, None
