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
            if 'entries' in info and info['entries']:
                entry = info['entries'][0]
                return entry.get('url'), entry.get('title'), entry.get('thumbnail'), entry.get('duration', 0), f"https://www.youtube.com/watch?v={entry.get('id')}", entry.get('uploader', 'Desconocido')
    except Exception as e:
        print(f"Error en yt_dlp: {e}")
    return None, None, None, 0, None, None

def get_spotify_track_name(url):
    try:
        track_info = sp.track(url)
        return f"{track_info['name']} {track_info['artists'][0]['name']}"
    except:
        return None

class MusicControls(discord.ui.View):
    def __init__(self, bot, ctx):
        super().__init__(timeout=None)
        self.bot = bot
        self.ctx = ctx

    @discord.ui.button(label="", emoji="⏯️", style=discord.ButtonStyle.primary)
    async def pause_resume(self, interaction, button):
        vc = self.ctx.voice_client
        if not vc:
            return await interaction.response.send_message("No estoy conectado.", ephemeral=True)
        if vc.is_playing():
            vc.pause()
            await interaction.response.send_message("Pausado.", ephemeral=True)
        elif vc.is_paused():
            vc.resume()
            await interaction.response.send_message("Reanudado.", ephemeral=True)

    @discord.ui.button(label="", emoji="⏭️", style=discord.ButtonStyle.secondary)
    async def next_song(self, interaction, button):
        vc = self.ctx.voice_client
        if not vc:
            return await interaction.response.send_message("No conectado.", ephemeral=True)
        if not queue:
            return await interaction.response.send_message("Cola vacía.", ephemeral=True)
        await interaction.response.defer()
        vc.stop()
        await play_next(self.ctx)

    @discord.ui.button(label="", emoji="⏹️", style=discord.ButtonStyle.danger)
    async def stop(self, interaction, button):
        vc = self.ctx.voice_client
        if not vc:
            return await interaction.response.send_message("No conectado.", ephemeral=True)
        queue.clear()
        vc.stop()
        await asyncio.sleep(0.5)
        await vc.disconnect()
        await interaction.response.send_message("Detenido y desconectado.", ephemeral=True)
        self.clear_items()

@bot.command()
async def play(ctx, *, query: str):
    if ctx.author.voice is None:
        return await ctx.send("Debes estar en un canal de voz.")

    vc = ctx.voice_client or await ctx.author.voice.channel.connect()
    if "spotify.com/track" in query:
        query = get_spotify_track_name(query)
        if not query:
            return await ctx.send("No se pudo obtener información de Spotify.")

    queue.append((query, ctx.author))
    await ctx.send(f"🎵 Añadido: **{query}**")
    if not vc.is_playing() and not vc.is_paused():
        await play_next(ctx)

async def play_next(ctx):
    if not queue:
        return

    query, requester = queue.pop(0)
    vc = ctx.voice_client
    if not vc:
        return

    url, title, thumb, dur, vid_url, uploader = get_youtube_url(query)
    if not url:
        return await play_next(ctx)

    if url.endswith(".m3u8"):
        return await play_next(ctx)

    source = discord.FFmpegPCMAudio(url, executable='ffmpeg', before_options='-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5', options='-vn')
    def after(e):
        if e:
            print(f"Error: {e}")
        asyncio.run_coroutine_threadsafe(play_next(ctx), bot.loop)

    vc.play(source, after=after)

    # Nuevo formato visual para la canción actual
    embed = discord.Embed(color=discord.Color.purple())
    embed.description = f"<a:cd:123456789012345678>  **{title}**"  # Aquí se usa el emoji :cd:
    embed.add_field(name="⏱️ Duración:", value=f"[{str(timedelta(seconds=dur))}]", inline=False)
    embed.add_field(name="👤 Solicitado por:", value=f"[{requester.mention}](https://discord.com/users/{requester.id})", inline=False)
    embed.set_thumbnail(url=thumb)
    await ctx.send(embed=embed, view=MusicControls(bot, ctx))

@bot.command()
async def leave(ctx):
    if ctx.voice_client:
        queue.clear()
        await ctx.voice_client.disconnect()
        await ctx.send("👋 Me salí del canal de voz.")

@bot.command()
async def comandos(ctx):
    desc = (
        "**Comandos disponibles:**\n"
        "-play <nombre>: Busca y reproduce música de YouTube o Spotify.\n"
        "-leave: Desconecta al bot.\n"
        "-comandos: Muestra este mensaje.\n"
        "-huevin <mensaje>: Habla con Huevin (solo canal autorizado y rol @Friends)."
    )
    await ctx.send(embed=discord.Embed(description=desc, color=discord.Color.teal()))

@bot.command()
async def huevin(ctx, *, message: str):
    if ctx.channel.id != ALLOWED_CHANNEL_ID:
        return await ctx.send(f"Este comando solo está permitido en <#{ALLOWED_CHANNEL_ID}>.")

    if not any(role.id == ALLOWED_ROLE_ID for role in ctx.author.roles):
        return await ctx.send("No tienes permiso para usar este comando, necesitas el rol @Friends.")

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
    activity = discord.Game(name="insultando inútiles")
    await bot.change_presence(activity=activity)
    print(f"Bot conectado como {bot.user}")

bot.run(os.getenv("DISCORD_TOKEN"))
