import discord
from discord.ext import commands
from spotipy import Spotify
from spotipy.oauth2 import SpotifyClientCredentials
import yt_dlp as youtube_dl
import os
from dotenv import load_dotenv
import asyncio
from openai import OpenAI
from datetime import datetime, timedelta

load_dotenv()

intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True

bot = commands.Bot(command_prefix='-', intents=intents)

# Configuración de Spotify
SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")
sp = Spotify(auth_manager=SpotifyClientCredentials(
    client_id=SPOTIFY_CLIENT_ID,
    client_secret=SPOTIFY_CLIENT_SECRET
))

# Configuración de OpenAI
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
openai_client = OpenAI(api_key=OPENAI_API_KEY)

queue = []
ALLOWED_CHANNEL_ID = 1108528856408805417
ALLOWED_ROLE_ID = 714948180617330728
user_conversations = {}
CONVERSATION_TIMEOUT = timedelta(minutes=30)
MAX_HISTORY = 3

# FUNCIONES DE SOPORTE
def manage_conversation(user_id, user_message, bot_response):
    current_time = datetime.now()
    if user_id not in user_conversations:
        user_conversations[user_id] = {'history': [], 'last_active': current_time}
    user_conversations[user_id]['history'].append({"role": "user", "content": user_message})
    user_conversations[user_id]['history'].append({"role": "assistant", "content": bot_response})
    user_conversations[user_id]['last_active'] = current_time
    if len(user_conversations[user_id]['history']) > MAX_HISTORY * 2:
        user_conversations[user_id]['history'] = user_conversations[user_id]['history'][-MAX_HISTORY * 2:]
    to_remove = [uid for uid, data in user_conversations.items() if current_time - data['last_active'] > CONVERSATION_TIMEOUT]
    for uid in to_remove:
        del user_conversations[uid]

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
        'format': 'bestaudio[ext=webm]/bestaudio[ext=m4a]/bestaudio',
        'quiet': True,
        'noplaylist': True,
        'default_search': 'ytsearch' if not is_url else None,
        'extract_flat': False,
        'no_warnings': True,
        'ignoreerrors': True,
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
            return info.get('url'), info.get('title'), info.get('thumbnail'), info.get('duration', 0), f"https://www.youtube.com/watch?v={info.get('id')}", info.get('uploader', 'Desconocido')
    except Exception as e:
        print(f"Error en yt_dlp: {e}")
        return None, None, None, 0, None, None

class MusicControls(discord.ui.View):
    def __init__(self, bot, ctx):
        super().__init__(timeout=None)
        self.bot = bot
        self.ctx = ctx

    @discord.ui.button(label="", emoji="⏯️", style=discord.ButtonStyle.primary)
    async def pause_resume(self, interaction: discord.Interaction, button):
        await interaction.response.defer(ephemeral=True)
        vc = self.ctx.voice_client
        if not vc:
            return await interaction.followup.send("No estoy conectado a ningún canal de voz.", ephemeral=True)
        if vc.is_playing():
            vc.pause()
            await interaction.followup.send("Pausado. ⏸️", ephemeral=True)
        elif vc.is_paused():
            vc.resume()
            await interaction.followup.send("Reanudado. ▶️", ephemeral=True)

    @discord.ui.button(label="", emoji="⏭️", style=discord.ButtonStyle.secondary)
    async def next_song(self, interaction: discord.Interaction, button):
        await interaction.response.defer(ephemeral=True)
        vc = self.ctx.voice_client
        if not vc:
            return await interaction.followup.send("No estoy conectado a ningún canal de voz.", ephemeral=True)
        if not queue:
            return await interaction.followup.send("La cola está vacía.", ephemeral=True)
        vc.stop()
        await play_next(self.ctx)

    @discord.ui.button(label="", emoji="⏹️", style=discord.ButtonStyle.danger)
    async def stop(self, interaction: discord.Interaction, button):
        await interaction.response.defer(ephemeral=True)
        vc = self.ctx.voice_client
        if not vc:
            return await interaction.followup.send("No estoy conectado a ningún canal de voz.", ephemeral=True)
        queue.clear()
        vc.stop()
        await asyncio.sleep(0.5)
        await vc.disconnect()
        await interaction.followup.send("Reproducción detenida y desconectado. 🛑", ephemeral=True)
        self.clear_items()

@bot.command()
async def play(ctx, *, query: str):
    if ctx.author.voice is None:
        return await ctx.send("Debes estar en un canal de voz para usar este comando. 🎙️")

    loading_msg = await ctx.send("🔄 Buscando y cargando la canción, espera un momento...")

    vc = ctx.voice_client or await ctx.author.voice.channel.connect()
    
    # Variables para la imagen y duración
    album_image = None
    dur = 0
    is_youtube_url = "youtube.com/watch?v=" in query or "youtu.be/" in query
    
    if is_youtube_url:
        # Si es un enlace de YouTube, obtenemos la info directamente
        url, title, thumb, dur, vid_url, uploader = get_youtube_info(query, is_url=True)
        if not url:
            await loading_msg.delete()
            return await ctx.send("No pude obtener la información del video de YouTube. Intenta con otro enlace. 🎵")
        query = title  # Usamos el título del video como query
        # Intentamos buscar en Spotify para obtener la carátula
        track_name, album_image, dur_spotify = search_spotify(query)
        if track_name:
            dur = dur_spotify if dur_spotify else dur
    elif "spotify.com/track" in query:
        # Si es un enlace de Spotify, obtenemos info directamente
        track_name, album_image, dur = get_spotify_track_info(query)
        if not track_name:
            await loading_msg.delete()
            return await ctx.send("No pude obtener la información de Spotify. Intenta con otra canción. 🎵")
        query = track_name
    else:
        # Si es una búsqueda por nombre, buscamos en Spotify
        track_name, album_image, dur = search_spotify(query)
        if track_name:
            query = track_name
        else:
            # Si no encontramos en Spotify, buscamos en YouTube
            url, title, thumb, dur, vid_url, uploader = get_youtube_info(query, is_url=False)
            if not url:
                await loading_msg.delete()
                return await ctx.send("No encontré esa canción en YouTube. Prueba con otra. 🔍")

    queue.append((query, ctx.author, album_image, dur, is_youtube_url))

    # Formatear el mensaje de "Añadido a la cola"
    duration_str = f"[{dur // 60:02d}:{dur % 60:02d}]"
    embed = discord.Embed(color=discord.Color.blue())
    embed.description = (
        f"**Añadido a la Cola** 🩸\n"
        f"**{query.split(' (')[0].strip()}** • {duration_str}\n"
        f"**Queue Length:** {len(queue)}"
    )
    if album_image:
        embed.set_thumbnail(url=album_image)
    await loading_msg.delete()
    await ctx.send(embed=embed)

    if not vc.is_playing() and not vc.is_paused():
        await play_next(ctx)

async def play_next(ctx):
    if not queue:
        return

    query, requester, album_image, dur, is_youtube_url = queue.pop(0)
    vc = ctx.voice_client
    if not vc:
        return

    # Buscamos en YouTube para reproducir
    url, title, thumb, dur_yt, vid_url, uploader = get_youtube_info(query, is_url=is_youtube_url)
    if not url:
        await ctx.send("No pude encontrar el video en YouTube, pasando a la siguiente canción...")
        return await play_next(ctx)

    if url.endswith(".m3u8"):
        await ctx.send("Formato no compatible (.m3u8), pasando a la siguiente canción...")
        return await play_next(ctx)

    # Usamos la duración de Spotify si está disponible, si no, la de YouTube
    dur = dur if dur else dur_yt

    try:
        source = discord.FFmpegPCMAudio(
            url,
            executable='ffmpeg',
            before_options='-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5 -loglevel quiet',
            options='-vn -bufsize 64k'
        )
        def after(e):
            if e:
                print(f"Error en reproducción: {e}")
            asyncio.run_coroutine_threadsafe(play_next(ctx), bot.loop)

        vc.play(source, after=after)

        embed = discord.Embed(color=discord.Color.blue())
        duration_str = f"[{dur // 60:02d}:{dur % 60:02d}]"
        embed.description = (
            f"**Reproduciendo** 🎶\n"
            f"**{title.split(' (')[0].strip()}** • {duration_str}\n"
            f"**Solicitado por:** {requester.mention}\n"
            f"**Canciones en cola:** {len(queue)}"
        )
        if album_image:
            embed.set_thumbnail(url=album_image)
        else:
            embed.set_thumbnail(url=thumb)

        await ctx.send(embed=embed, view=MusicControls(bot, ctx))

    except Exception as e:
        print(f"Error detallado al reproducir: {str(e)}")
        await ctx.send(f"Hubo un error al reproducir la canción: {str(e)}. Pasando a la siguiente...")
        await play_next(ctx)

@bot.command()
async def leave(ctx):
    if ctx.voice_client:
        queue.clear()
        await ctx.voice_client.disconnect()
        await ctx.send("👋 Me salí del canal de voz. ¡Nos vemos!")
    else:
        await ctx.send("No estoy en ningún canal de voz. ¿Qué quieres que haga? 🤔")

@bot.command()
async def comandos(ctx):
    desc = (
        "**Comandos disponibles:**\n"
        "-play <nombre>: Busca y reproduce música de YouTube o Spotify. 🎵\n"
        "-leave: Desconecta al bot del canal de voz. 👋\n"
        "-comandos: Muestra esta lista de comandos. 📜\n"
        "-huevin <mensaje>: Habla con Huevín (solo en el canal autorizado y con el rol @Friends). 😈"
    )
    await ctx.send(embed=discord.Embed(description=desc, color=discord.Color.teal()))

@bot.command()
async def huevin(ctx, *, message: str):
    if ctx.channel.id != ALLOWED_CHANNEL_ID:
        return await ctx.send(f"Este comando solo se puede usar en <#{ALLOWED_CHANNEL_ID}>. ¡Muévete pa’llá! 🚫")

    if not any(role.id == ALLOWED_ROLE_ID for role in ctx.author.roles):
        return await ctx.send("No tienes permiso para usar este comando. Necesitas el rol @Friends. 🔒")

    user_id = ctx.author.id
    conversation = user_conversations.get(user_id, {'history': []})['history']

    messages = [
        {"role": "system", "content": "Habla con humor negro y sarcasmo cabrón. Usa apodos duros. Máx 60 palabras."}
    ] + conversation + [{"role": "user", "content": message}]

    response = openai_client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=messages,
        max_tokens=75,
        temperature=1.0
    )
    reply = response.choices[0].message.content.strip()

    manage_conversation(user_id, message, reply)
    await ctx.send(f"{ctx.author.mention} {reply}")

@bot.event
async def on_ready():
    activity = discord.Game(name="insultando pendejos")
    await bot.change_presence(activity=activity)
    print(f"Bot conectado como {bot.user}")

bot.run(os.getenv("DISCORD_TOKEN"))
