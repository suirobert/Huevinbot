import discord
from discord.ext import commands
from spotipy import Spotify
from spotipy.oauth2 import SpotifyClientCredentials
import yt_dlp as youtube_dl
import os
from dotenv import load_dotenv
import asyncio
from openai import OpenAI
from datetime import datetime

load_dotenv()

intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True

bot = commands.Bot(command_prefix='!', intents=intents)

# Spotify setup
SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")
sp = Spotify(auth_manager=SpotifyClientCredentials(
    client_id=SPOTIFY_CLIENT_ID,
    client_secret=SPOTIFY_CLIENT_SECRET
))

# OpenAI setup
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
openai_client = OpenAI(api_key=OPENAI_API_KEY)

# Cola de reproducción
queue = []

# ID del canal permitido para !huevin
ALLOWED_CHANNEL_ID = 1108528856408805417

# Función para obtener el enlace, título, miniatura y duración de YouTube
def get_youtube_url(search_query):
    ydl_opts = {
        'format': 'bestaudio[ext=webm]',
        'quiet': True,
        'noplaylist': True,
        'default_search': 'ytsearch',
        'extract_flat': False,
    }
    try:
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(f"ytsearch:{search_query}", download=False)
            if 'entries' in info and len(info['entries']) > 0:
                entry = info['entries'][0]
                audio_url = entry.get('url')
                title = entry.get('title')
                thumbnail = entry.get('thumbnail')
                duration = entry.get('duration', 0)
                video_url = f"https://www.youtube.com/watch?v={entry.get('id')}"
                uploader = entry.get('uploader', 'Desconocido')
                return audio_url, title, thumbnail, duration, video_url, uploader
            else:
                return None, None, None, 0, None, None
    except Exception as e:
        print(f"Error en yt_dlp: {e}")
        return None, None, None, 0, None, None

# Función para extraer nombre de canción de Spotify
def get_spotify_track_name(url):
    try:
        track_info = sp.track(url)
        return f"{track_info['name']} {track_info['artists'][0]['name']}"
    except Exception as e:
        print(f"Error en Spotify: {e}")
        return None

# Clase para los botones de control
class MusicControls(discord.ui.View):
    def __init__(self, bot, ctx):
        super().__init__(timeout=None)
        self.bot = bot
        self.ctx = ctx

    @discord.ui.button(label="", emoji="⏯️", style=discord.ButtonStyle.primary)
    async def pause_resume(self, interaction: discord.Interaction, button: discord.ui.Button):
        voice_client = self.ctx.voice_client
        if not voice_client:
            await interaction.response.send_message("No estoy conectado a un canal de voz.", ephemeral=True)
            return
        if voice_client.is_playing():
            voice_client.pause()
            await interaction.response.send_message("Pausado.", ephemeral=True)
        elif voice_client.is_paused():
            voice_client.resume()
            await interaction.response.send_message("Reanudado.", ephemeral=True)
        else:
            await interaction.response.send_message("No hay nada reproduciendo.", ephemeral=True)

    @discord.ui.button(label="", emoji="⏭️", style=discord.ButtonStyle.secondary)
    async def next_song(self, interaction: discord.Interaction, button: discord.ui.Button):
        voice_client = self.ctx.voice_client
        if not voice_client:
            await interaction.response.send_message("No estoy conectado a un canal de voz.", ephemeral=True)
            return
        if not queue:
            await interaction.response.send_message("No hay más canciones en la cola.", ephemeral=True)
            return
        
        await interaction.response.defer()
        loading_message = await self.ctx.send(embed=discord.Embed(description="⏳ Buscando la siguiente canción...", color=discord.Color.blue()))
        voice_client.stop()
        await play_next(self.ctx)
        await loading_message.delete()

    @discord.ui.button(label="", emoji="⏹️", style=discord.ButtonStyle.danger)
    async def stop(self, interaction: discord.Interaction, button: discord.ui.Button):
        voice_client = self.ctx.voice_client
        if not voice_client:
            await interaction.response.send_message("No estoy conectado a un canal de voz.", ephemeral=True)
            return
        queue.clear()
        voice_client.stop()
        await asyncio.sleep(0.5)
        await voice_client.disconnect()
        await interaction.response.send_message("Reproducción detenida y desconectado.", ephemeral=True)
        self.clear_items()

@bot.command()
async def play(ctx, *, query: str):
    try:
        if ctx.author.voice is None:
            await ctx.send(embed=discord.Embed(description="Debes estar en un canal de voz.", color=discord.Color.red()))
            return

        voice_client = ctx.voice_client
        if not voice_client:
            voice_client = await ctx.author.voice.channel.connect()

        if "spotify.com/track" in query:
            query = get_spotify_track_name(query)
            if not query:
                await ctx.send(embed=discord.Embed(description="No se pudo obtener la información de Spotify.", color=discord.Color.red()))
                return

        queue.append(query)
        await ctx.send(embed=discord.Embed(description=f"🎵 Añadido a la cola: **{query}**", color=discord.Color.green()))
        if not voice_client.is_playing() and not voice_client.is_paused():
            loading_message = await ctx.send(embed=discord.Embed(description="⏳ Buscando canción...", color=discord.Color.blue()))
            await play_next(ctx)
            await loading_message.delete()
    except Exception as e:
        await ctx.send(embed=discord.Embed(description=f"Ocurrió un error: {str(e)}", color=discord.Color.red()))
        print(f"Error en play: {e}")

async def play_next(ctx):
    try:
        if not queue:
            return

        query = queue.pop(0)
        voice_client = ctx.voice_client
        if not voice_client:
            return

        audio_url, title, thumbnail, duration, video_url, uploader = get_youtube_url(query)
        if not audio_url:
            await ctx.send(embed=discord.Embed(description="No se encontró ningún resultado en YouTube.", color=discord.Color.red()))
            await play_next(ctx)
            return

        if audio_url.endswith(".m3u8") or audio_url.startswith("https://www.youtube.com/"):
            await ctx.send(embed=discord.Embed(description="Error: Formato de audio no compatible (HLS o URL inválida).", color=discord.Color.red()))
            await play_next(ctx)
            return

        ffmpeg_options = {
            'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5 -re',
            'options': '-vn -bufsize 64k'
        }
        audio_source = discord.FFmpegPCMAudio(
            audio_url,
            executable='ffmpeg',
            **ffmpeg_options
        )

        def after_playing(error):
            if error:
                print(f"Error al reproducir: {error}")
            asyncio.run_coroutine_threadsafe(play_next(ctx), bot.loop)

        embed = discord.Embed(color=discord.Color.blue())
        embed.set_author(name="Ahora reproduciendo 🎵", icon_url=bot.user.avatar.url if bot.user.avatar else None)
        embed.title = title
        if video_url:
            embed.url = video_url
        embed.add_field(name="Canal", value=uploader, inline=True)
        duration_seconds = int(duration) if duration else 0
        embed.add_field(name="Duración", value=f"{duration_seconds // 60}:{duration_seconds % 60:02d}" if duration_seconds else "Desconocida", inline=True)
        embed.add_field(name="En cola", value=str(len(queue)), inline=True)
        if thumbnail:
            embed.set_thumbnail(url=thumbnail)
        embed.set_footer(text="Usa los botones para controlar la reproducción")

        voice_client.play(audio_source, after=after_playing)
        await ctx.send(embed=embed, view=MusicControls(bot, ctx))

    except Exception as e:
        await ctx.send(embed=discord.Embed(description=f"Ocurrió un error: {str(e)}", color=discord.Color.red()))
        print(f"Error en play_next: {e}")
        if ctx.voice_client and ctx.voice_client.is_playing():
            ctx.voice_client.stop()

@bot.command()
async def queue_add(ctx, *, query: str):
    queue.append(query)
    await ctx.send(embed=discord.Embed(description=f"🎵 Añadido a la cola: **{query}**", color=discord.Color.green()))

@bot.command()
async def queue_list(ctx):
    if not queue:
        await ctx.send(embed=discord.Embed(description="La cola está vacía.", color=discord.Color.orange()))
        return
    embed = discord.Embed(title="Cola de reproducción", color=discord.Color.green())
    for i, song in enumerate(queue, 1):
        embed.add_field(name=f"{i}.", value=song, inline=False)
    await ctx.send(embed=embed)

@bot.command()
async def clear(ctx):
    if not queue:
        await ctx.send(embed=discord.Embed(description="La cola ya está vacía.", color=discord.Color.orange()))
        return
    queue.clear()
    await ctx.send(embed=discord.Embed(description="🗑️ La cola ha sido limpiada.", color=discord.Color.green()))

@bot.command()
async def leave(ctx):
    if ctx.voice_client:
        queue.clear()
        await ctx.voice_client.disconnect()
        await ctx.send(embed=discord.Embed(description="👋 Me salí del canal de voz.", color=discord.Color.blue()))
    else:
        await ctx.send(embed=discord.Embed(description="No estoy conectado a ningún canal de voz.", color=discord.Color.red()))

@bot.command(name="comandos")
async def comandos(ctx):
    embed = discord.Embed(title="📜 Comandos disponibles", color=discord.Color.purple())
    embed.add_field(name="🎧 !play [canción o link]", value="Reproduce una canción desde YouTube o Spotify.", inline=False)
    embed.add_field(name="➕ !queue_add [canción]", value="Agrega una canción a la cola.", inline=False)
    embed.add_field(name="📋 !queue_list", value="Muestra la cola de canciones actual.", inline=False)
    embed.add_field(name="🧹 !clear", value="Limpia toda la cola de reproducción.", inline=False)
    embed.add_field(name="👋 !leave", value="Saca al bot del canal de voz y limpia la cola.", inline=False)
    embed.add_field(name="🧠 !huevin [mensaje]", value="Interactúa con el bot (solo en canal permitido). Responde con humor negro y sarcasmo.", inline=False)
    embed.add_field(name="ℹ️ !comandos", value="Muestra esta lista de comandos disponibles.", inline=False)
    await ctx.send(embed=embed)

# Comando !huevin con GPT-3.5-turbo
@bot.command()
async def huevin(ctx, *, message: str):
    try:
        if ctx.channel.id != ALLOWED_CHANNEL_ID:
            channel = bot.get_channel(ALLOWED_CHANNEL_ID)
            channel_name = channel.name if channel else f"el canal con ID {ALLOWED_CHANNEL_ID}"
            await ctx.send(f"{ctx.author.mention} Qué va, este comando es solo para #{channel_name}. ¡Muévete pa’llá!")
            return

        messages = [
            {
                "role": "system",
                "content": (
                    "Habla con humor negro y sarcasmo cabrón, sin filtros. Usa apodos duros (inútil, pendejo, cerebrito). "
                    "Respuestas cortas, directas, máximo 60 palabras."
                )
            },
            {"role": "user", "content": message}
        ]

        response = openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages,
            max_tokens=75,
            temperature=1.0
        )

        reply = response.choices[0].message.content.strip()
        token_usage = response.usage.total_tokens if response.usage else "N/A"

        print(f"[GPT LOG] {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Usuario: {ctx.author.name} ({ctx.author.id}) - Mensaje: '{message}' - Tokens: {token_usage}")
        await ctx.send(f"{ctx.author.mention} {reply}")

    except Exception as e:
        await ctx.send(f"{ctx.author.mention} ¡La cagué! Error: {str(e)}")
        print(f"Error en huevin: {e}")

@bot.event
async def on_voice_state_update(member, before, after):
    if member == bot.user and before.channel and not after.channel:
        print("Bot desconectado del canal de voz.")
        queue.clear()
        if hasattr(bot, 'last_channel') and bot.last_channel:
            try:
                await bot.last_channel.send(embed=discord.Embed(description="Fui desconectado del canal de voz. La cola ha sido limpiada.", color=discord.Color.red()))
            except discord.errors.Forbidden:
                print("No se pudo enviar mensaje de desconexión: permisos insuficientes.")
        bot.last_channel = None

@bot.event
async def on_command(ctx):
    bot.last_channel = ctx.channel

bot.run(os.getenv("DISCORD_TOKEN"))
