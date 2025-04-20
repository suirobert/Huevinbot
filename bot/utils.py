import re
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from yt_dlp import YoutubeDL
import os
from dotenv import load_dotenv

load_dotenv()
SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")

# Configuración de Spotify
sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(client_id=SPOTIFY_CLIENT_ID, client_secret=SPOTIFY_CLIENT_SECRET))

def get_youtube_info(query, is_url=False):
    ydl_opts = {
        'format': 'bestaudio/best',
        'quiet': True,  # Silenciar logs detallados
        'no_warnings': True,  # No mostrar advertencias
        'cookiefile': 'cookies.txt',  # Usar cookies para evitar bloqueos
        'noplaylist': True,  # No procesar playlists
        'extract_flat': True,  # No descargar, solo extraer información
        'force_generic_extractor': True,
    }
    try:
        with YoutubeDL(ydl_opts) as ydl:
            if is_url:
                info = ydl.extract_info(query, download=False)
            else:
                info = ydl.extract_info(f"ytsearch:{query}", download=False)
                if 'entries' in info and info['entries']:
                    info = info['entries'][0]
            url = info.get('url')
            title = info.get('title')
            thumbnail = info.get('thumbnail')
            duration = info.get('duration')
            vid_url = info.get('webpage_url')
            uploader = info.get('uploader')
            return url, title, thumbnail, duration, vid_url, uploader
    except Exception as e:
        print(f"Error al obtener información de YouTube: {str(e)}")
        return None, None, None, 0, None, None

def get_youtube_playlist_info(url):
    ydl_opts = {
        'format': 'bestaudio/best',
        'quiet': True,  # Silenciar logs detallados
        'no_warnings': True,  # No mostrar advertencias
        'cookiefile': 'cookies.txt',  # Usar cookies para evitar bloqueos
        'extract_flat': True,  # Solo extraer información, no descargar
    }
    try:
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            if 'entries' not in info:
                return [], "Unknown Playlist"
            playlist_name = info.get('title', "Unknown Playlist")
            tracks = []
            for entry in info['entries']:
                track_url = entry.get('url') or entry.get('webpage_url')
                track_name = entry.get('title')
                thumbnail = entry.get('thumbnail')
                duration = entry.get('duration', 0)
                tracks.append((track_url, track_name, thumbnail, duration))
            return tracks, playlist_name
    except Exception as e:
        print(f"Error al obtener playlist de YouTube: {str(e)}")
        return [], "Unknown Playlist"

def search_spotify(query):
    try:
        results = sp.search(q=query, type='track', limit=1)
        if results['tracks']['items']:
            track = results['tracks']['items'][0]
            track_name = f"{track['artists'][0]['name']} - {track['name']}"
            album_image = track['album']['images'][0]['url'] if track['album']['images'] else None
            duration = track['duration_ms'] // 1000
            return track_name, album_image, duration
        return None, None, 0
    except Exception as e:
        print(f"Error al buscar en Spotify: {str(e)}")
        return None, None, 0

def get_spotify_track_info(url):
    try:
        track_id = url.split('/')[-1].split('?')[0]
        track = sp.track(track_id)
        track_name = f"{track['artists'][0]['name']} - {track['name']}"
        album_image = track['album']['images'][0]['url'] if track['album']['images'] else None
        duration = track['duration_ms'] // 1000
        return track_name, album_image, duration
    except Exception as e:
        print(f"Error al obtener información de pista de Spotify: {str(e)}")
        return None, None, 0

def get_spotify_playlist_info(url):
    try:
        playlist_id = url.split('/')[-1].split('?')[0]
        playlist = sp.playlist(playlist_id)
        playlist_name = playlist['name']
        tracks = []
        for item in playlist['tracks']['items']:
            track = item['track']
            if track:
                track_url = track['external_urls']['spotify']
                track_name = f"{track['artists'][0]['name']} - {track['name']}"
                album_image = track['album']['images'][0]['url'] if track['album']['images'] else None
                duration = track['duration_ms'] // 1000
                tracks.append((track_url, track_name, album_image, duration))
        return tracks, playlist_name
    except Exception as e:
        print(f"Error al obtener playlist de Spotify: {str(e)}")
        return [], "Unknown Playlist"
