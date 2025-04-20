import discord
import asyncio
import concurrent.futures
import random
from bot.utils import get_youtube_info, search_spotify, get_spotify_track_info, get_spotify_playlist_info, get_youtube_playlist_info

# Colas y configuraciones
queue = []  # Cola principal: (url_or_query, display_name, requester, album_image, dur, is_youtube_url)
audio_ready_queue = []  # Cola secundaria: (url, display_name, requester, album_image, dur, thumb)
currently_playing = None  # Canción actualmente en reproducción: (url, display_name, requester, album_image, dur, thumb)
skip_flag = False
executor = concurrent.futures.ThreadPoolExecutor(max_workers=2)
current_message = None  # Referencia al mensaje actual de reproducción
queue_messages = []  # Lista de mensajes relacionados con la cola
processing_task = None  # Para controlar la tarea de procesamiento en segundo plano

# Función para ejecutar tareas pesadas en un hilo separado
async def run_in_executor(func, *args):
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(executor, func, *args)

# Procesar una sola canción y añadirla a audio_ready_queue
async def process_single_song(ctx, song_info):
    global audio_ready_queue
    url_or_query, display_name, requester, album_image, dur, is_youtube_url = song_info
    url, title, thumb, dur_yt, vid_url, uploader = await run_in_executor(get_youtube_info, url_or_query, is_youtube_url)
    if url and not url.endswith(".m3u8"):
        dur = dur if dur else dur_yt
        audio_ready_queue.append((url, title or display_name, requester, album_image, dur, thumb))
        return True
    else:
        await ctx.send(f"No pude encontrar '{display_name}' en YouTube. Se omite de la cola. 🎶")
        return False

# Procesar las próximas canciones de la cola principal (máximo 3 a la vez)
async def process_next_songs(ctx):
    global queue, audio_ready_queue, processing_task
    while len(audio_ready_queue) < 3 and queue:
        song_info = queue.pop(0)
        await process_single_song(ctx, song_info)
    if audio_ready_queue and not ctx.voice_client.is_playing() and not ctx.voice_client.is_paused():
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
        global skip_flag, current_message, processing_task
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
        # Asegurarse de que siempre haya canciones listas para reproducir
        if len(audio_ready_queue) < 3 and queue:
            if processing_task and not processing_task.done():
                processing_task.cancel()
                await asyncio.sleep(0.1)
            processing_task = asyncio.create_task(process_next_songs(self.ctx))
        await play_next(self.ctx)

    @discord.ui.button(label="", emoji="🔀", style=discord.ButtonStyle.grey)
    async def shuffle(self, interaction: discord.Interaction, button):
        global queue, audio_ready_queue, processing_task
        await interaction.response.defer(ephemeral=True)
        vc = self.ctx.voice_client
        if not vc:
            return await interaction.followup.send("No estoy conectado a ningún canal de voz. 🎙️", ephemeral=True)
        if not queue and not audio_ready_queue:
            return await interaction.followup.send("La cola está vacía. ¡Añade algunas canciones primero! 🎵", ephemeral=True)
        
        # Cancelar cualquier tarea de procesamiento en curso
        if processing_task and not processing_task.done():
            processing_task.cancel()
            await asyncio.sleep(0.1)  # Dar tiempo para que la tarea se cancele
        
        # Mezclar las colas sin interrumpir la canción actual
        combined_queue = audio_ready_queue + [(url_or_query, display_name, requester, album_image, dur, False) for url_or_query, display_name, requester, album_image, dur, _ in queue]
        random.shuffle(combined_queue)
        audio_ready_queue = []
        queue = []
        for item in combined_queue:
            if len(item) == 6 and item[5] is not False:  # Es una entrada de audio_ready_queue
                audio_ready_queue.append(item)
            else:  # Es una entrada de queue
                queue.append((item[0], item[1], item[2], item[3], item[4], False))
        
        # Procesar la primera canción de inmediato si no hay canciones listas
        if not audio_ready_queue and queue:
            first_song = queue.pop(0)
            await process_single_song(self.ctx, first_song)
        
        await interaction.followup.send("🔀 ¡Cola mezclada! Las próximas canciones se reproducirán en orden aleatorio.", ephemeral=True)
        
        # Iniciar el procesamiento en segundo plano para las canciones restantes
        if queue:
            processing_task = asyncio.create_task(process_next_songs(self.ctx))

    @discord.ui.button(label="", emoji="📜", style=discord.ButtonStyle.grey)
    async def show_queue(self, interaction: discord.Interaction, button):
        await interaction.response.defer(ephemeral=True)
        if not audio_ready_queue and not queue:
            return await interaction.followup.send("La cola está vacía. ¡Añade algunas canciones! 🎵", ephemeral=True)
        
        # Tomar una instantánea de las colas para evitar discrepancias
        current_audio_ready = audio_ready_queue.copy()
        current_queue = queue.copy()
        
        embed = discord.Embed(title="📜 Cola de Canciones", color=discord.Color.blue())
        description = ""
        # Estandarizar el formato de las entradas para asegurar consistencia
        combined_queue = []
        for item in current_audio_ready:
            url, display_name, requester, album_image, dur, thumb = item
            combined_queue.append((url, display_name, requester, album_image, dur, thumb))
        for item in current_queue:
            url_or_query, display_name, requester, album_image, dur, is_youtube_url = item
            combined_queue.append((None, display_name, requester, album_image, dur, None))
        
        for i, item in enumerate(combined_queue[:10], 1):
            _, display_name, requester, _, dur, _ = item
            duration_str = f"[{dur // 60:02d}:{dur % 60:02d}]"
            description += f"**{i}.** {display_name.split(' (')[0].strip()} • {duration_str} (por {requester.mention})\n"
        if len(combined_queue) > 10:
            description += f"\nY {len(combined_queue) - 10} más..."
        embed.description = description
        queue_msg = await interaction.followup.send(embed=embed, ephemeral=True)
        queue_messages.append(queue_msg)

    @discord.ui.button(label="", emoji="⏹️", style=discord.ButtonStyle.danger)
    async def stop(self, interaction: discord.Interaction, button):
        global skip_flag, current_message, queue_messages, processing_task, currently_playing
        await interaction.response.defer(ephemeral=True)
        vc = self.ctx.voice_client
        if not vc:
            return await interaction.followup.send("No estoy conectado a ningún canal de voz. 🎙️", ephemeral=True)
        queue.clear()
        audio_ready_queue.clear()
        currently_playing = None
        if processing_task and not processing_task.done():
            processing_task.cancel()
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
    global skip_flag, current_message, queue_messages, processing_task, currently_playing
    
    # Limpiar mensajes de "Añadido a la Cola" después de que comience la reproducción
    for msg in queue_messages:
        try:
            await msg.delete()
        except discord.HTTPException:
            pass
    queue_messages.clear()

    if not audio_ready_queue:
        if queue:
            first_song = queue.pop(0)
            await process_single_song(ctx, first_song)
            # Iniciar procesamiento en segundo plano para las canciones restantes
            if queue:
                processing_task = asyncio.create_task(process_next_songs(ctx))
        else:
            currently_playing = None
            return

    if not audio_ready_queue:
        currently_playing = None
        return

    # Actualizar la canción actualmente en reproducción
    currently_playing = audio_ready_queue.pop(0)
    url, display_name, requester, album_image, dur, thumb = currently_playing
    vc = ctx.voice_client
    if not vc:
        currently_playing = None
        return

    try:
        if vc.is_playing() or vc.is_paused():
            skip_flag = True
            vc.stop()
            await asyncio.sleep(1.0)

        source = discord.FFmpegPCMAudio(
            url,
            executable='ffmpeg',
            before_options='-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5 -loglevel error',  # Cambiado a "error" para menos logs
            options='-vn -bufsize 64k -af "aresample=48000" -ac 2 -ar 48000 -f s16le -acodec pcm_s16le'  # Añadimos opciones para asegurar compatibilidad
        )
        def after(e):
            global skip_flag
            if e:
                print(f"Error en reproducción: {e}")
            if not skip_flag:
                asyncio.run_coroutine_threadsafe(play_next(ctx), ctx.bot.loop)
            skip_flag = False

        vc.play(source, after=after)

        # Usar los datos de currently_playing para el mensaje
        embed = discord.Embed(color=discord.Color.blue())
        duration_str = f"[{dur // 60:02d}:{dur % 60:02d}]"
        embed.description = (
            f"**Reproduciendo Ahora**\n"
            f"{display_name.split(' (')[0].strip()} • {duration_str}\n"
            f"[{requester.mention}]"
        )
        if album_image:
            embed.set_thumbnail(url=album_image)
        else:
            embed.set_thumbnail(url=thumb)

        if current_message:
            try:
                await current_message.delete()
            except discord.HTTPException:
                pass
        current_message = await ctx.send(embed=embed, view=MusicControls(ctx.bot, ctx))

    except Exception as e:
        print(f"Error al reproducir {display_name}: {str(e)}")
        await ctx.send(f"Hubo un error al reproducir la canción: {str(e)}. Pasando a la siguiente... 🎶")
        currently_playing = None
        await play_next(ctx)

def setup_music_commands(bot):
    @bot.command(name="play")
    async def play(ctx, *, query: str):
        global queue, queue_messages, processing_task
        if ctx.author.voice is None:
            return await ctx.send("Debes estar en un canal de voz para usar este comando. 🎙️")

        loading_msg = await ctx.send("🔄 Buscando y cargando, espera un momento...")

        vc = ctx.voice_client or await ctx.author.voice.channel.connect()
        
        # Mejorar la detección de URLs de YouTube y playlists
        is_youtube_url = "youtube.com/watch?v=" in query or "youtu.be/" in query
        is_youtube_playlist = "list=" in query or "youtube.com/playlist" in query
        is_spotify_track = "spotify.com/track" in query
        is_spotify_playlist = "spotify.com/playlist" in query
        original_url = query if is_youtube_url else None
        
        if is_spotify_playlist:
            playlist_tracks, playlist_name = await run_in_executor(get_spotify_playlist_info, query)
            if not playlist_tracks:
                await loading_msg.delete()
                return await ctx.send("No pude obtener las canciones de la playlist. Intenta con otra. 🎵")
            
            # Procesar solo la primera canción de inmediato
            if playlist_tracks:
                first_track = playlist_tracks[0]
                track_url, track_name, album_image, dur = first_track
                song_info = (track_url, track_name, ctx.author, album_image, dur, False)
                if await process_single_song(ctx, song_info):
                    pass
                else:
                    await loading_msg.delete()
                    return await ctx.send(f"No se pudo procesar la primera canción de la playlist '{playlist_name}'. Intenta con otra. 🎵")
            
            # Añadir el resto de las canciones a la cola
            for track in playlist_tracks[1:]:
                track_url, track_name, album_image, dur = track
                queue.append((track_url, track_name, ctx.author, album_image, dur, False))
            
            embed = discord.Embed(color=discord.Color.blue())
            embed.description = (
                f"**Añadidas {len(playlist_tracks)} canciones a la cola desde la playlist '{playlist_name}'** 🩸\n"
                f"Las canciones están siendo procesadas, ¡la reproducción comenzará pronto!"
            )
            await loading_msg.delete()
            msg = await ctx.send(embed=embed)
            queue_messages.append(msg)

            # Iniciar procesamiento en segundo plano para las canciones restantes
            if queue:
                processing_task = asyncio.create_task(process_next_songs(ctx))

        elif is_youtube_playlist:
            playlist_tracks, playlist_name = await run_in_executor(get_youtube_playlist_info, query)
            if not playlist_tracks:
                await loading_msg.delete()
                return await ctx.send("No pude obtener las canciones de la playlist de YouTube. Intenta con otra. 🎵")
            
            # Procesar solo la primera canción de inmediato
            if playlist_tracks:
                first_track = playlist_tracks[0]
                track_url, track_name, album_image, dur = first_track
                song_info = (track_url, track_name, ctx.author, album_image, dur, True)
                if await process_single_song(ctx, song_info):
                    pass
                else:
                    await loading_msg.delete()
                    return await ctx.send(f"No se pudo procesar la primera canción de la playlist '{playlist_name}'. Intenta con otra. 🎵")
            
            # Añadir el resto de las canciones a la cola
            for track in playlist_tracks[1:]:
                track_url, track_name, album_image, dur = track
                queue.append((track_url, track_name, ctx.author, album_image, dur, True))
            
            embed = discord.Embed(color=discord.Color.blue())
            embed.description = (
                f"**Añadidas {len(playlist_tracks)} canciones a la cola desde la playlist '{playlist_name}'** 🩸\n"
                f"Las canciones están siendo procesadas, ¡la reproducción comenzará pronto!"
            )
            await loading_msg.delete()
            msg = await ctx.send(embed=embed)
            queue_messages.append(msg)

            # Iniciar procesamiento en segundo plano para las canciones restantes
            if queue:
                processing_task = asyncio.create_task(process_next_songs(ctx))

        else:
            album_image = None
            dur = 0
            display_name = query
            if is_youtube_url:
                # Obtener la información directamente de YouTube
                url, title, thumb, dur_yt, vid_url, uploader = await run_in_executor(get_youtube_info, query, is_youtube_url)
                if not url:
                    await loading_msg.delete()
                    return await ctx.send("No pude obtener el video de YouTube. Intenta con otro enlace. 🎵")
                display_name = title or query
                album_image = thumb
                dur = dur_yt
            elif is_spotify_track:
                track_name, album_image, dur = await run_in_executor(get_spotify_track_info, query)
                if not track_name:
                    await loading_msg.delete()
                    return await ctx.send("No pude obtener la información de Spotify. Intenta con otra canción. 🎵")
                display_name = track_name
            else:
                track_name, album_image, dur = await run_in_executor(search_spotify, query)
                if track_name:
                    display_name = track_name

            song_info = (original_url or display_name, display_name, ctx.author, album_image, dur, is_youtube_url)
            # Procesar la canción de inmediato y solo añadir a la cola si se procesa correctamente
            if await process_single_song(ctx, song_info):
                duration_str = f"[{dur // 60:02d}:{dur % 60:02d}]"
                embed = discord.Embed(color=discord.Color.blue())
                embed.description = (
                    f"**Añadido a la Cola** 🩸\n"
                    f"{display_name.split(' (')[0].strip()} • {duration_str}\n"
                )
                await loading_msg.delete()
                msg = await ctx.send(embed=embed)
                queue_messages.append(msg)
            else:
                await loading_msg.delete()
                return

        # Comenzar la reproducción si hay canciones listas
        if audio_ready_queue and not vc.is_playing() and not vc.is_paused():
            await play_next(ctx)

    @bot.command()
    async def shuffle(ctx):
        global queue, audio_ready_queue, processing_task
        vc = ctx.voice_client
        if not vc:
            return await ctx.send("No estoy conectado a ningún canal de voz. 🎙️")
        if not queue and not audio_ready_queue:
            return await ctx.send("La cola está vacía. ¡Añade algunas canciones primero! 🎵")
        
        # Cancelar cualquier tarea de procesamiento en curso
        if processing_task and not processing_task.done():
            processing_task.cancel()
            await asyncio.sleep(0.1)  # Dar tiempo para que la tarea se cancele
        
        # Mezclar las colas sin interrumpir la canción actual
        combined_queue = audio_ready_queue + [(url_or_query, display_name, requester, album_image, dur, False) for url_or_query, display_name, requester, album_image, dur, _ in queue]
        random.shuffle(combined_queue)
        audio_ready_queue = []
        queue = []
        for item in combined_queue:
            if len(item) == 6 and item[5] is not False:  # Es una entrada de audio_ready_queue
                audio_ready_queue.append(item)
            else:  # Es una entrada de queue
                queue.append((item[0], item[1], item[2], item[3], item[4], False))
        
        # Procesar la primera canción de inmediato si no hay canciones listas
        if not audio_ready_queue and queue:
            first_song = queue.pop(0)
            await process_single_song(ctx, first_song)
        
        await ctx.send("🔀 ¡Cola mezclada! Las próximas canciones se reproducirán en orden aleatorio.")
        
        # Iniciar procesamiento en segundo plano para las canciones restantes
        if queue:
            processing_task = asyncio.create_task(process_next_songs(ctx))

    @bot.command()
    async def queue(ctx):
        global queue, audio_ready_queue
        if not audio_ready_queue and not queue:
            return await ctx.send("La cola está vacía. ¡Añade algunas canciones! 🎵")
        
        # Tomar una instantánea de las colas para evitar discrepancias
        current_audio_ready = audio_ready_queue.copy()
        current_queue = queue.copy()
        
        embed = discord.Embed(title="📜 Cola de Canciones", color=discord.Color.blue())
        description = ""
        # Estandarizar el formato de las entradas para asegurar consistencia
        combined_queue = []
        for item in current_audio_ready:
            url, display_name, requester, album_image, dur, thumb = item
            combined_queue.append((url, display_name, requester, album_image, dur, thumb))
        for item in current_queue:
            url_or_query, display_name, requester, album_image, dur, is_youtube_url = item
            combined_queue.append((None, display_name, requester, album_image, dur, None))
        
        for i, item in enumerate(combined_queue[:10], 1):
            _, display_name, requester, _, dur, _ = item
            duration_str = f"[{dur // 60:02d}:{dur % 60:02d}]"
            description += f"**{i}.** {display_name.split(' (')[0].strip()} • {duration_str} (por {requester.mention})\n"
        if len(combined_queue) > 10:
            description += f"\nY {len(combined_queue) - 10} más..."
        embed.description = description
        await ctx.send(embed=embed)

    @bot.command()
    async def leave(ctx):
        global skip_flag, current_message, queue_messages, processing_task, currently_playing
        if ctx.voice_client:
            queue.clear()
            audio_ready_queue.clear()
            currently_playing = None
            if processing_task and not processing_task.done():
                processing_task.cancel()
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
