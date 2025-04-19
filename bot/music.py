import discord
import asyncio
import concurrent.futures
import random
from .utils import get_youtube_info, search_spotify, get_spotify_track_info, get_spotify_playlist_info

# Colas y configuraciones
queue = []  # Cola principal: almacena información básica de las canciones
audio_ready_queue = []  # Cola secundaria: almacena canciones con audio listo para reproducir
skip_flag = False
executor = concurrent.futures.ThreadPoolExecutor(max_workers=2)
current_message = None  # Referencia al mensaje actual de reproducción
queue_messages = []  # Lista de mensajes relacionados con la cola

# Función para ejecutar tareas pesadas en un hilo separado
async def run_in_executor(func, *args):
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(executor, func, *args)

# Procesar las próximas canciones de la cola principal (máximo 3 a la vez)
async def process_next_songs(ctx):
    global queue, audio_ready_queue
    while len(audio_ready_queue) < 3 and queue:
        song_info = queue.pop(0)
        url_or_query, display_query, requester, album_image, dur, is_youtube_url = song_info
        url, title, thumb, dur_yt, vid_url, uploader = await run_in_executor(get_youtube_info, url_or_query, is_youtube_url)
        if url and not url.endswith(".m3u8"):
            dur = dur if dur else dur_yt
            audio_ready_queue.append((url, display_query, requester, album_image, dur, thumb))
            print(f"Canción procesada y añadida a audio_ready_queue: {display_query}")
        else:
            print(f"No se pudo procesar {display_query}, se omite.")
            await ctx.send(f"No pude encontrar '{display_query}' en YouTube. Se omite de la cola. 🎶")
    if audio_ready_queue and not ctx.voice_client.is_playing() and not ctx.voice_client.is_paused():
        print("Llamando a play_next desde process_next_songs")
        await play_next(ctx)

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
            return await interaction.followup.send("No estoy conectado a ningún canal de voz. 🎙️", ephemeral=True)
        if vc.is_playing():
            vc.pause()
            await interaction.followup.send("Pausado. ⏸️", ephemeral=True)
        elif vc.is_paused():
            vc.resume()
            await interaction.followup.send("Reanudado. ▶️", ephemeral=True)

    @discord.ui.button(label="", emoji="⏭️", style=discord.ButtonStyle.secondary)
    async def next_song(self, interaction: discord.Interaction, button):
        global skip_flag, current_message
        await interaction.response.defer(ephemeral=True)
        vc = self.ctx.voice_client
        if not vc:
            return await interaction.followup.send("No estoy conectado a ningún canal de voz. 🎙️", ephemeral=True)
        if not audio_ready_queue and not queue:
            return await interaction.followup.send("La cola está vacía. 🎶", ephemeral=True)
        if vc.is_playing() or vc.is_paused():
            skip_flag = True
            vc.stop()
            await asyncio.sleep(1.0)
        # Eliminar el mensaje anterior
        if current_message:
            try:
                await current_message.delete()
            except discord.HTTPException:
                pass
            current_message = None
        print(f"Estado del voice_client después de stop: is_playing={vc.is_playing()}, is_paused={vc.is_paused()}")
        await play_next(self.ctx)

    @discord.ui.button(label="", emoji="🔀", style=discord.ButtonStyle.grey)
    async def shuffle(self, interaction: discord.Interaction, button):
        global queue, audio_ready_queue
        await interaction.response.defer(ephemeral=True)
        vc = self.ctx.voice_client
        if not vc:
            return await interaction.followup.send("No estoy conectado a ningún canal de voz. 🎙️", ephemeral=True)
        if not queue and not audio_ready_queue:
            return await interaction.followup.send("La cola está vacía. ¡Añade algunas canciones primero! 🎵", ephemeral=True)
        
        # Mezclar las colas sin interrumpir la canción actual
        combined_queue = audio_ready_queue + [(url_or_query, display_query, requester, album_image, dur, False) for url_or_query, display_query, requester, album_image, dur, _ in queue]
        random.shuffle(combined_queue)
        audio_ready_queue = []
        queue = []
        for item in combined_queue:
            if len(item) == 6 and item[5] is not False:  # Es una entrada de audio_ready_queue
                audio_ready_queue.append(item)
            else:  # Es una entrada de queue
                queue.append((item[0], item[1], item[2], item[3], item[4], False))
        
        await interaction.followup.send("🔀 ¡Cola mezclada! Las próximas canciones se reproducirán en orden aleatorio.", ephemeral=True)
        
        # Procesar las próximas canciones (sin interrumpir la reproducción actual)
        asyncio.create_task(process_next_songs(self.ctx))

    @discord.ui.button(label="", emoji="📜", style=discord.ButtonStyle.grey)
    async def show_queue(self, interaction: discord.Interaction, button):
        await interaction.response.defer(ephemeral=True)
        if not audio_ready_queue and not queue:
            return await interaction.followup.send("La cola está vacía. ¡Añade algunas canciones! 🎵", ephemeral=True)
        
        embed = discord.Embed(title="📜 Cola de Canciones", color=discord.Color.blue())
        description = ""
        combined_queue = audio_ready_queue + [(url_or_query, display_query, requester, album_image, dur, None) for url_or_query, display_query, requester, album_image, dur, _ in queue]
        for i, item in enumerate(combined_queue[:10], 1):
            if len(item) == 6 and item[5] is not None:  # Es una entrada de audio_ready_queue
                _, display_query, requester, _, dur, _ = item
            else:  # Es una entrada de queue
                _, display_query, requester, _, dur, _ = item
            duration_str = f"[{dur // 60:02d}:{dur % 60:02d}]"
            description += f"**{i}.** {display_query.split(' (')[0].strip()} • {duration_str} (por {requester.mention})\n"
        if len(combined_queue) > 10:
            description += f"\nY {len(combined_queue) - 10} más..."
        embed.description = description
        queue_msg = await interaction.followup.send(embed=embed, ephemeral=True)
        queue_messages.append(queue_msg)

    @discord.ui.button(label="", emoji="⏹️", style=discord.ButtonStyle.danger)
    async def stop(self, interaction: discord.Interaction, button):
        global skip_flag, current_message, queue_messages
        await interaction.response.defer(ephemeral=True)
        vc = self.ctx.voice_client
        if not vc:
            return await interaction.followup.send("No estoy conectado a ningún canal de voz. 🎙️", ephemeral=True)
        queue.clear()
        audio_ready_queue.clear()
        if vc.is_playing() or vc.is_paused():
            skip_flag = True
            vc.stop()
            await asyncio.sleep(1.0)
        await vc.disconnect()
        # Limpiar mensajes
        if current_message:
            try:
                await current_message.delete()
            except discord.HTTPException:
                pass
            current_message = None
        for msg in queue_messages:
            try:
                await msg.delete()
            except discord.HTTPException:
                pass
        queue_messages.clear()
        await interaction.followup.send("Reproducción detenida y desconectado. 🛑", ephemeral=True)
        self.clear_items()

async def play_next(ctx):
    global skip_flag, current_message, queue_messages
    # Procesar más canciones si es necesario
    if len(audio_ready_queue) < 3:
        asyncio.create_task(process_next_songs(ctx))

    if not audio_ready_queue:
        print("No hay canciones en audio_ready_queue para reproducir.")
        return

    url, display_query, requester, album_image, dur, thumb = audio_ready_queue.pop(0)
    vc = ctx.voice_client
    if not vc:
        print("No hay voice_client disponible.")
        return

    print(f"Intentando reproducir: {display_query}")
    try:
        if vc.is_playing() or vc.is_paused():
            print("Voice client todavía está reproduciendo o pausado. Deteniendo antes de continuar...")
            skip_flag = True
            vc.stop()
            await asyncio.sleep(1.0)

        source = discord.FFmpegPCMAudio(
            url,
            executable='ffmpeg',
            before_options='-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5 -loglevel quiet',
            options='-vn -bufsize 64k -af "aresample=48000"'
        )
        def after(e):
            global skip_flag
            if e:
                print(f"Error en reproducción: {e}")
            if not skip_flag:
                asyncio.run_coroutine_threadsafe(play_next(ctx), bot.loop)
            skip_flag = False

        vc.play(source, after=after)
        print(f"Reproduciendo: {display_query}")

        embed = discord.Embed(color=discord.Color.blue())
        duration_str = f"[{dur // 60:02d}:{dur % 60:02d}]"
        embed.description = (
            f"**Reproduciendo Ahora**\n"
            f"{display_query.split(' (')[0].strip()} • {duration_str}\n"
            f"[{requester.mention}]"
        )
        if album_image:
            embed.set_thumbnail(url=album_image)
        else:
            embed.set_thumbnail(url=thumb)

        current_message = await ctx.send(embed=embed, view=MusicControls(ctx.bot, ctx))

    except Exception as e:
        print(f"Error detallado al reproducir {display_query}: {str(e)}")
        await ctx.send(f"Hubo un error al reproducir la canción: {str(e)}. Pasando a la siguiente... 🎶")
        await play_next(ctx)

def setup_music_commands(bot):
    @bot.command(name="play")
    async def play(ctx, *, query: str):
        global queue, queue_messages
        if ctx.author.voice is None:
            return await ctx.send("Debes estar en un canal de voz para usar este comando. 🎙️")

        loading_msg = await ctx.send("🔄 Buscando y cargando, espera un momento...")

        vc = ctx.voice_client or await ctx.author.voice.channel.connect()
        
        is_youtube_url = "youtube.com/watch?v=" in query or "youtu.be/" in query
        is_spotify_track = "spotify.com/track" in query
        is_spotify_playlist = "spotify.com/playlist" in query
        original_url = query if is_youtube_url else None
        
        if is_spotify_playlist:
            playlist_tracks, playlist_name = await run_in_executor(get_spotify_playlist_info, query)
            if not playlist_tracks:
                await loading_msg.delete()
                return await ctx.send("No pude obtener las canciones de la playlist. Intenta con otra. 🎵")
            
            print(f"Añadiendo {len(playlist_tracks)} canciones a la cola...")
            for track_name, album_image, dur in playlist_tracks:
                queue.append((track_name, track_name, ctx.author, album_image, dur, False))
                print(f"Canción añadida a queue: {track_name}")
            
            embed = discord.Embed(color=discord.Color.blue())
            embed.description = (
                f"**Añadidas {len(playlist_tracks)} canciones a la cola desde la playlist '{playlist_name}'** 🩸\n"
            )
            await loading_msg.delete()
            msg = await ctx.send(embed=embed)
            queue_messages.append(msg)

            # Procesar las primeras canciones y comenzar la reproducción
            if not vc.is_playing() and not vc.is_paused():
                print("Procesando primeras canciones después de añadir playlist...")
                await process_next_songs(ctx)

        else:
            album_image = None
            dur = 0
            if is_youtube_url:
                track_name, album_image, dur = await run_in_executor(search_spotify, query)
                if track_name:
                    display_query = track_name
                else:
                    display_query = query
            elif is_spotify_track:
                track_name, album_image, dur = await run_in_executor(get_spotify_track_info, query)
                if not track_name:
                    await loading_msg.delete()
                    return await ctx.send("No pude obtener la información de Spotify. Intenta con otra canción. 🎵")
                display_query = track_name
            else:
                track_name, album_image, dur = await run_in_executor(search_spotify, query)
                if track_name:
                    display_query = track_name
                else:
                    display_query = query

            queue.append((original_url or display_query, display_query, ctx.author, album_image, dur, is_youtube_url))
            print(f"Canción añadida a queue: {display_query}")

            duration_str = f"[{dur // 60:02d}:{dur % 60:02d}]"
            embed = discord.Embed(color=discord.Color.blue())
            embed.description = (
                f"**Añadido a la Cola** 🩸\n"
                f"{display_query.split(' (')[0].strip()} • {duration_str}\n"
            )
            await loading_msg.delete()
            msg = await ctx.send(embed=embed)
            queue_messages.append(msg)

            # Procesar las primeras canciones y comenzar la reproducción
            if not vc.is_playing() and not vc.is_paused():
                print("Procesando primera canción después de añadir una sola pista...")
                await process_next_songs(ctx)

    @bot.command()
    async def shuffle(ctx):
        global queue, audio_ready_queue
        vc = ctx.voice_client
        if not vc:
            return await ctx.send("No estoy conectado a ningún canal de voz. 🎙️")
        if not queue and not audio_ready_queue:
            return await ctx.send("La cola está vacía. ¡Añade algunas canciones primero! 🎵")
        
        # Mezclar las colas sin interrumpir la canción actual
        combined_queue = audio_ready_queue + [(url_or_query, display_query, requester, album_image, dur, False) for url_or_query, display_query, requester, album_image, dur, _ in queue]
        random.shuffle(combined_queue)
        audio_ready_queue = []
        queue = []
        for item in combined_queue:
            if len(item) == 6 and item[5] is not False:  # Es una entrada de audio_ready_queue
                audio_ready_queue.append(item)
            else:  # Es una entrada de queue
                queue.append((item[0], item[1], item[2], item[3], item[4], False))
        
        await ctx.send("🔀 ¡Cola mezclada! Las próximas canciones se reproducirán en orden aleatorio.")
        
        # Procesar las próximas canciones (sin interrumpir la reproducción actual)
        asyncio.create_task(process_next_songs(ctx))

    @bot.command()
    async def queue(ctx):
        global queue, audio_ready_queue
        if not audio_ready_queue and not queue:
            return await ctx.send("La cola está vacía. ¡Añade algunas canciones! 🎵")
        
        embed = discord.Embed(title="📜 Cola de Canciones", color=discord.Color.blue())
        description = ""
        combined_queue = audio_ready_queue + [(url_or_query, display_query, requester, album_image, dur, None) for url_or_query, display_query, requester, album_image, dur, _ in queue]
        for i, item in enumerate(combined_queue[:10], 1):
            if len(item) == 6 and item[5] is not None:  # Es una entrada de audio_ready_queue
                _, display_query, requester, _, dur, _ = item
            else:  # Es una entrada de queue
                _, display_query, requester, _, dur, _ = item
            duration_str = f"[{dur // 60:02d}:{dur % 60:02d}]"
            description += f"**{i}.** {display_query.split(' (')[0].strip()} • {duration_str} (por {requester.mention})\n"
        if len(combined_queue) > 10:
            description += f"\nY {len(combined_queue) - 10} más..."
        embed.description = description
        await ctx.send(embed=embed)

    @bot.command()
    async def leave(ctx):
        global skip_flag, current_message, queue_messages
        if ctx.voice_client:
            queue.clear()
            audio_ready_queue.clear()
            if ctx.voice_client.is_playing() or ctx.voice_client.is_paused():
                skip_flag = True
                ctx.voice_client.stop()
                await asyncio.sleep(1.0)
            await ctx.voice_client.disconnect()
            # Limpiar mensajes
            if current_message:
                try:
                    await current_message.delete()
                except discord.HTTPException:
                    pass
                current_message = None
            for msg in queue_messages:
                try:
                    await msg.delete()
                except discord.HTTPException:
                    pass
            queue_messages.clear()
            await ctx.send("👋 Me salí del canal de voz. ¡Nos vemos!")
        else:
            await ctx.send("No estoy en ningún canal de voz. ¿Qué quieres que haga? 🤔")

    @bot.command()
    async def comandos(ctx):
        desc = (
            "**Comandos disponibles:**\n"
            "-play <nombre o enlace>: Busca y reproduce música de YouTube o Spotify (soporta playlists). 🎵\n"
            "-shuffle: Mezcla la cola de canciones para reproducirlas en orden aleatorio. 🔀\n"
            "-queue: Muestra la cola de canciones. 📜\n"
            "-leave: Desconecta al bot del canal de voz. 👋\n"
            "-comandos: Muestra esta lista de comandos. 📜\n"
            "-huevin <mensaje>: Habla con Huevín (solo en el canal autorizado y con el rol @Friends). 😈"
        )
        await ctx.send(embed=discord.Embed(description=desc, color=discord.Color.teal()))
