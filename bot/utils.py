import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import yt_dlp
from bot.config import SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET

# Configuración de Spotify
sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(client_id=SPOTIFY_CLIENT_ID, client_secret=SPOTIFY_CLIENT_SECRET))

def get_youtube_info(query, is_youtube_url):
    """Busca información de un video en YouTube."""
    ydl_opts = {
        'format': 'bestaudio/best',
        'noplaylist': True,
        'quiet': True,
        'no_warnings': True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(query, download=False)
            return (
                info.get('url'),
                info.get('title'),
                info.get('thumbnail'),
                info.get('duration'),
                info.get('webpage_url'),
                info.get('uploader')
            )
        except Exception as e:
            print(f"Error al buscar en YouTube: {e}")
            return None, None, None, 0, None, None

def search_spotify(query):
    """Busca una canción en Spotify y devuelve su nombre, imagen y duración."""
    try:
        results = sp.search(q=query, type='track', limit=1)
        track = results['tracks']['items'][0]
        return (
            f"{track['name']} ({track['artists'][0]['name']})",
            track['album']['images'][0]['url'] if track['album']['images'] else None,
            track['duration_ms'] // 1000
        )
    except Exception as e:
        print(f"Error al buscar en Spotify: {e}")
        return None, None, 0

def get_spotify_track_info(track_url):
    """Obtiene información de una pista de Spotify a partir de su URL."""
    try:
        track_id = track_url.split('/')[-1].split('?')[0]
        track = sp.track(track_id)
        return (
            f"{track['name']} ({track['artists'][0]['name']})",
            track['album']['images'][0]['url'] if track['album']['images'] else None,
            track['duration_ms'] // 1000
        )
    except Exception as e:
        print(f"Error al obtener pista de Spotify: {e}")
        return None, None, 0

def get_spotify_playlist_info(playlist_url):
    """Obtiene información de una playlist de Spotify."""
    try:
        playlist_id = playlist_url.split('/')[-1].split('?')[0]
        playlist = sp.playlist(playlist_id)
        tracks = playlist['tracks']['items']
        playlist_name = playlist['name']
        track_list = []
        for item in tracks:
            track = item['track']
            track_list.append((
                f"{track['name']} ({track['artists'][0]['name']})",
                f"{track['name']} ({track['artists'][0]['name']})",
                track['album']['images'][0]['url'] if track['album']['images'] else None,
                track['duration_ms'] // 1000
            ))
        return track_list, playlist_name
    except Exception as e:
        print(f"Error al obtener playlist de Spotify: {e}")
        return [], ""

def get_youtube_playlist_info(playlist_url):
    """Obtiene información de una playlist de YouTube."""
    ydl_opts = {
        'extract_flat': True,
        'quiet': True,
        'no_warnings': True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(playlist_url, download=False)
            playlist_name = info.get('title', 'Playlist')
            track_list = []
            for entry in info['entries']:
                track_list.append((
                    entry['url'],
                    entry['title'],
                    None,  # YouTube no proporciona imagen de álbum directamente
                    entry.get('duration', 0)
                ))
            return track_list, playlist_name
        except Exception as e:
            print(f"Error al obtener playlist de YouTube: {e}")
            return [], ""
