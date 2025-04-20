import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import yt_dlp
from bot.config import SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET
import re

# Configuración de Spotify
sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(client_id=SPOTIFY_CLIENT_ID, client_secret=SPOTIFY_CLIENT_SECRET))

def get_youtube_info(query, is_youtube_url):
    """Busca información de un video en YouTube."""
    ydl_opts = {
        'format': 'bestaudio/best',
        'noplaylist': True,
        'quiet': True,
        'no_warnings': True,
        'default_search': 'ytsearch' if not is_youtube_url else None,
        'extractor_args': {
            'youtube': {
                'skip_download': True,
                'geo_bypass': True,
            }
        }
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            print(f"[get_youtube_info] Buscando: {query}, is_youtube_url={is_youtube_url}")
            if is_youtube_url:
                info = ydl.extract_info(query, download=False)
            else:
                info = ydl.extract_info(f"ytsearch:{query}", download=False)
                info = info['entries'][0] if 'entries' in info and info['entries'] else None
            if not info:
                print("[get_youtube_info] No se encontró información para la consulta.")
                return None, None, None, 0, None, None
            print(f"[get_youtube_info] Encontrado: {info.get('title')}, URL: {info.get('url')}")
            return (
                info.get('url'),
                info.get('title'),
                info.get('thumbnail'),
                info.get('duration', 0),
                info.get('webpage_url'),
                info.get('uploader')
            )
        except Exception as e:
            print(f"[get_youtube_info] Error al buscar en YouTube: {e}")
            return None, None, None, 0, None, None

def search_spotify(query):
    """Busca una canción en Spotify y devuelve su nombre, imagen y duración."""
    try:
        print(f"[search_spotify] Buscando: {query}")
        results = sp.search(q=query, type='track', limit=1)
        track = results['tracks']['items'][0]
        print(f"[search_spotify] Encontrado: {track['name']} ({track['artists'][0]['name']})")
        return (
            f"{track['name']} ({track['artists'][0]['name']})",
            track['album']['images'][0]['url'] if track['album']['images'] else None,
            track['duration_ms'] // 1000
        )
    except Exception as e:
        print(f"[search_spotify] Error al buscar en Spotify: {e}")
        return None, None, 0

def get_spotify_track_info(track_url):
    """Obtiene información de una pista de Spotify a partir de su URL."""
    try:
        print(f"[get_spotify_track_info] Obteniendo pista: {track_url}")
        track_id = track_url.split('/')[-1].split('?')[0]
        track = sp.track(track_id)
        print(f"[get_spotify_track_info] Encontrado: {track['name']} ({track['artists'][0]['name']})")
        return (
            f"{track['name']} ({track['artists'][0]['name']})",
            track['album']['images'][0]['url'] if track['album']['images'] else None,
            track['duration_ms'] // 1000
        )
    except Exception as e:
        print(f"[get_spotify_track_info] Error al obtener pista de Spotify: {e}")
        return None, None, 0

def get_spotify_playlist_info(playlist_url):
    """Obtiene información de una playlist de Spotify."""
    try:
        print(f"[get_spotify_playlist_info] Obteniendo playlist: {playlist_url}")
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
        print(f"[get_spotify_playlist_info] Encontradas {len(track_list)} canciones en la playlist: {playlist_name}")
        return track_list, playlist_name
    except Exception as e:
        print(f"[get_spotify_playlist_info] Error al obtener playlist de Spotify: {e}")
        return [], ""

def get_youtube_playlist_info(playlist_url):
    """Obtiene información de una playlist de YouTube."""
    # Extraer el ID de la playlist de la URL
    playlist_id_match = re.search(r'list=([a-zA-Z0-9_-]+)', playlist_url)
    if playlist_id_match:
        playlist_id = playlist_id_match.group(1)
        playlist_url_clean = f"https://www.youtube.com/playlist?list={playlist_id}"
        print(f"[get_youtube_playlist_info] URL ajustada a playlist pura: {playlist_url_clean}")
    else:
        print(f"[get_youtube_playlist_info] No se encontró un ID de playlist en la URL: {playlist_url}")
        return [], ""

    ydl_opts = {
        'extract_flat': True,
        'quiet': False,
        'no_warnings': False,
        'ignoreerrors': True,
        'verbose': True,
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
        },
        'extractor_args': {
            'youtube': {
                'skip_download': True,
                'geo_bypass': True,
                'force_generic_extractor': False,
                'playlist_items': '1-100',
            }
        }
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            print(f"[get_youtube_playlist_info] Obteniendo playlist: {playlist_url_clean}")
            ydl.params['verbose'] = True  # Forzamos verbose para más detalles
            info = ydl.extract_info(playlist_url_clean, download=False)
            print(f"[get_youtube_playlist_info] Información obtenida: {info}")
            if info is None:
                print("[get_youtube_playlist_info] No se obtuvo información de la playlist (info es None).")
                return [], ""
            if 'entries' not in info or not info['entries']:
                print("[get_youtube_playlist_info] No se encontraron entradas en la playlist de YouTube.")
                return [], ""
            playlist_name = info.get('title', 'Playlist')
            track_list = []
            for entry in info['entries']:
                if not entry:
                    print("[get_youtube_playlist_info] Entrada vacía, omitiendo.")
                    continue
                track_list.append((
                    entry['url'],
                    entry['title'],
                    None,
                    entry.get('duration', 0)
                ))
                print(f"[get_youtube_playlist_info] Añadida entrada: {entry['title']}")
            print(f"[get_youtube_playlist_info] Encontradas {len(track_list)} canciones en la playlist: {playlist_name}")
            return track_list, playlist_name
        except yt_dlp.utils.DownloadError as de:
            print(f"[get_youtube_playlist_info] Error de descarga en yt-dlp: {str(de)}")
            import traceback
            print(traceback.format_exc())
            return [], ""
        except Exception as e:
            print(f"[get_youtube_playlist_info] Error inesperado al obtener playlist de YouTube: {str(e)}")
            import traceback
            print(traceback.format_exc())
            return [], ""
