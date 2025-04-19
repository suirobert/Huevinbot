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

def get_spotify_playlist_info(playlist_url):
    try:
        playlist_id = playlist_url.split("playlist/")[1].split("?")[0]
        playlist_info = sp.playlist(playlist_id)
        playlist_name = playlist_info['name']  # Obtener el nombre de la playlist
        tracks = playlist_info['tracks']['items']
        playlist_tracks = []
        for item in tracks:
            track = item['track']
            if track:
                track_name = f"{track['name']} {track['artists'][0]['name']}"
                album_image = track['album']['images'][0]['url'] if track['album']['images'] else None
                duration_ms = track['duration_ms']
                duration_sec = duration_ms // 1000
                playlist_tracks.append((track_name, album_image, duration_sec))
        return playlist_tracks, playlist_name  # Devolver tanto las canciones como el nombre
    except Exception as e:
        print(f"Error al obtener info de la playlist de Spotify: {e}")
        return [], "Desconocida"

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

def get_youtube_playlist_info(playlist_url):
    """
    Obtiene la información de una playlist de YouTube.
    Retorna: (tracks, playlist_name)
    tracks: Lista de tuplas (track_name, album_image, duration)
    playlist_name: Nombre de la playlist
    """
    # Extraer el ID de la playlist de la URL
    playlist_id = None
    if "list=" in playlist_url:
        playlist_id = playlist_url.split("list=")[1].split("&")[0]
    elif "youtube.com/playlist" in playlist_url:
        playlist_id = playlist_url.split("list=")[1].split("&")[0] if "list=" in playlist_url else None
    
    if not playlist_id:
        print(f"No se pudo extraer el ID de la playlist de la URL: {playlist_url}")
        return [], "Desconocida"
    
    # Construir una URL específica para la playlist
    clean_playlist_url = f"https://www.youtube.com/playlist?list={playlist_id}"
    print(f"Procesando playlist de YouTube con URL: {clean_playlist_url}")

    ydl_opts = {
        'extract_flat': True,  # Solo extraer metadata, sin descargar
        'quiet': True,
        'no_warnings': True,
        'ignoreerrors': True,
        'playlist_items': '1-1000',  # Limitar a 1000 videos para evitar problemas con playlists muy grandes
    }
    try:
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(clean_playlist_url, download=False)
            if not info:
                print("No se obtuvo información de la playlist.")
                return [], "Desconocida"
            
            if 'entries' not in info or not info['entries']:
                print("No se encontraron videos en la playlist o la playlist no es accesible.")
                return [], "Desconocida"
            
            playlist_name = info.get('title', 'Desconocida')
            print(f"Nombre de la playlist: {playlist_name}, número de videos: {len(info['entries'])}")
            
            tracks = []
            for entry in info['entries']:
                if not entry:
                    print("Entrada vacía en la playlist, omitiendo...")
                    continue
                track_name = entry.get('title', 'Desconocido')
                duration = int(entry.get('duration', 0))  # Duración en segundos
                album_image = entry.get('thumbnail', None)  # Usar la miniatura como imagen del álbum
                video_id = entry.get('id', None)
                if video_id:
                    # Construir la URL del video para usarla como track_name
                    video_url = f"https://www.youtube.com/watch?v={video_id}"
                    tracks.append((video_url, album_image, duration))
                    print(f"Video añadido: {track_name}, duración: {duration} segundos")
                else:
                    print(f"No se pudo obtener el ID del video para: {track_name}, omitiendo...")
            return tracks, playlist_name
    except youtube_dl.utils.DownloadError as de:
        print(f"Error de descarga en yt-dlp: {str(de)}")
        return [], "Desconocida"
    except Exception as e:
        print(f"Error inesperado al obtener la playlist de YouTube: {str(e)}")
        return [], "Desconocida"
