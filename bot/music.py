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
monitor_task = None  # Para controlar la tarea de monitoreo de desconexión

# ID del canal de música
MUSIC_CHANNEL_ID = 1109369173580185640

# Chequeo personalizado para restringir comandos al canal de música
def music_channel_only():
    async def predicate(ctx):
        if ctx.channel.id != MUSIC_CHANNEL_ID:
            await ctx.send(f"Este comando solo se puede usar en el canal de música <#{MUSIC_CHANNEL_ID}>.")
            return False
        return True
    return discord.ext.commands.check(predicate)

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
        audio_ready_queue.append((url, display_name, requester, album_image, dur, thumb))
        print(f"Canción procesada y añadida a audio_ready_queue: {display_name}, URL: {url}")
        return True
    else:
        print(f"No se pudo procesar {display_name}, se omite.")
        await ctx.send(f"No pude encontrar '{display_name}' en YouTube. Se omite de la cola. 🎶")
        return False

# Procesar las próximas canciones de la cola principal (máximo 3 a la vez)
async def process_next_songs(ctx):
    global queue, audio_ready_queue, processing_task
    while len(audio_ready_queue) < 3 and queue:
        song_info = queue.pop(0)
        if await process_single_song(ctx, song_info):
            print(f"Cola actualizada: audio_ready_queue={[(item[1], item[4]) for item in audio_ready_queue]}, queue={[(item[1], item[4]) for item in queue]}")
    if audio_ready_queue and not ctx.voice_client.is_playing() and not ctx.voice_client.is_paused():
        print("Llamando a play_next desde process_next_songs")
        await play_next(ctx)

class MusicControls(discord.ui.View):
    def __init__(self, bot, ctx):
        super().__init__(timeout=None)
        self.bot = bot
        self.ctx = ctx

    async def check_channel(self, interaction: discord.Interaction):
        if interaction.channel_id != MUSIC_CHANNEL_ID:
            await interaction.followup.send(
                f"Esta acción solo se puede realizar en el canal de música <#{MUSIC_CHANNEL_ID}>.",
                ephemeral=True
            )
            return False
        return True

    @discord.ui.button(label="", emoji="⏯️", style=discord.ButtonStyle.primary)
    async def pause_resume(self, interaction: discord.Interaction, button):
        await interaction.response.defer(ephemeral=True)
        if not await self.check_channel(interaction):
            return
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
        if not await self.check_channel(interaction):
            return
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
        print(f"Cola antes de reproducir siguiente (next_song): audio_ready_queue={[(item[1], item[4]) for item in audio_ready_queue]}, queue={[(item[1], item[4]) for item in queue]}")
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
        if not await self.check_channel(interaction):
            return
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
        
        print(f"Cola después de shuffle: audio_ready_queue={[(item[1], item[4]) for item in audio_ready_queue]}, queue={[(item[1], item[4]) for item in queue]}")
        
        # Procesar la primera canción de inmediato si no hay canciones listas
        if not audio_ready_queue and queue:
            first_song = queue.pop(0)
            if await process_single_song(self.ctx, first_song):
                print(f"Primera canción después de shuffle procesada: {first_song[1]}")
        
        await interaction.followup.send("🔀 ¡Cola mezclada! Las próximas canciones se reproducirán en orden aleatorio.", ephemeral=True)
        
        # Iniciar procesamiento en segundo plano para las canciones restantes
        if queue:
            processing_task = asyncio.create_task(process_next_songs(self.ctx))

    @discord.ui.button(label="", emoji="📜", style=discord.ButtonStyle.grey)
    async def show_queue(self, interaction: discord.Interaction, button):
        await interaction.response.defer(ephemeral=True)
        if not await self.check_channel(interaction):
            return
        if not audio_ready_queue and not queue:
            return await interaction.followup.send("La cola está vacía. ¡Añade algunas canciones! 🎵", ephemeral=True)
        
        # Tomar una instantánea de las colas para evitar discrepancias
        current_audio_ready = audio_ready_queue.copy()
        current_queue = queue.copy()
        
        # Depuración: Mostrar el contenido de las colas
        print(f"[show_queue] audio_ready_queue: {[(item[1], item[4]) for item in current_audio_ready]}")
        print(f"[show_queue] queue: {[(item[1], item[4]) for item in current_queue]}")
        
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
        global skip_flag, current_message, queue_messages, processing_task, currently_playing, monitor_task
        await interaction.response.defer(ephemeral=True)
        if not await self.check_channel(interaction):
            return
        vc = self.ctx.voice_client
        if not vc:
            return await interaction.followup.send("No estoy conectado a ningún canal de voz. 🎙️", ephemeral=True)
        queue.clear()
        audio_ready_queue.clear()
        currently_playing = None
        if processing_task and not processing_task.done():
            processing_task.cancel()
        if monitor_task and not monitor_task.done():
            monitor_task.cancel()
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
    global skip_flag, current_message, queue_messages, processing_task, currently_playing, monitor_task
    print(f"[play_next] Iniciando función play_next")
    print(f"[play_next] audio_ready_queue: {[(item[1], item[4]) for item in audio_ready_queue]}")
    
    # Limpiar mensajes de "Añadido a la Cola" después de que comience la reproducción
    for msg in queue_messages:
        try:
            await msg.delete()
        except discord.HTTPException:
            pass
    queue_messages.clear()

    if not audio_ready_queue:
        print("No hay canciones en audio_ready_queue para reproducir.")
        if queue:
            print("Procesando canciones restantes en queue...")
            first_song = queue.pop(0)
            if await process_single_song(ctx, first_song):
                print(f"Primera canción procesada en play_next: {first_song[1]}")
            # Iniciar procesamiento en segundo plano para las canciones restantes
            if queue:
                processing_task = asyncio.create_task(process_next_songs(ctx))
        else:
            print("No hay más canciones en queue. Deteniendo reproducción.")
            currently_playing = None
            return

    if not audio_ready_queue:
        print("No hay más canciones para reproducir después de procesar queue.")
        currently_playing = None
        return

    # Actualizar la canción actualmente en reproducción
    print(f"[play_next] Actualizando currently_playing con la próxima canción")
    currently_playing = audio_ready_queue.pop(0)
    print(f"[play_next] currently_playing actualizado: {currently_playing[1]} (duración: {currently_playing[4]} segundos)")
    
    url, display_name, requester, album_image, dur, thumb = currently_playing
    vc = ctx.voice_client
    if not vc:
        print("No hay voice_client disponible.")
        currently_playing = None
        return

    print(f"Intentando reproducir: {display_name}, URL: {url}")
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
                print("Reproducción finalizada, llamando a play_next.")
                asyncio.run_coroutine_threadsafe(play_next(ctx), ctx.bot.loop)
            else:
                print("Reproducción detenida por skip_flag.")
            skip_flag = False

        vc.play(source, after=after)
        print(f"Reproduciendo: {display_name}")

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
        print(f"[play_next] Enviando mensaje de 'Reproduciendo Ahora' para: {display_name}")
        current_message = await ctx.send(embed=embed, view=MusicControls(ctx.bot, ctx))

        # Reiniciar el monitoreo de actividad
        if monitor_task and not monitor_task.done():
            monitor_task.cancel()
        monitor_task = asyncio.create_task(monitor_disconnect(ctx))

    except Exception as e:
        print(f"Error detallado al reproducir {display_name}: {str(e)}")
        await ctx.send(f"Hubo un error al reproducir la canción: {str(e)}. Pasando a la siguiente... 🎶")
        currently_playing = None
        await play_next(ctx)

async def monitor_disconnect(ctx):
    """Monitorea la desconexión automática si no hay usuarios o actividad."""
    global monitor_task, current_message, queue_messages, currently_playing
    vc = ctx.voice_client
    last_activity = asyncio.get_event_loop().time()  # Tiempo de la última actividad
    empty_channel_count = 0  # Contador para 5 minutos sin usuarios
    inactivity_count = 0  # Contador para 30 minutos sin canciones

    while vc and vc.is_connected():
        current_time = asyncio.get_event_loop().time()
        channel_members = vc.channel.members
        has_users = any(member.bot is False for member in channel_members)  # Excluir bots

        # Actualizar última actividad si hay cola o reproducción
        if audio_ready_queue or queue or (currently_playing and vc.is_playing()):
            last_activity = current_time

        # Verificar si el canal está vacío
        if not has_users:
            empty_channel_count += 1
            print(f"[monitor_disconnect] Canal vacío por {empty_channel_count * 30} segundos")
            if empty_channel_count >= 10:  # 10 * 30 segundos = 5 minutos
                print("[monitor_disconnect] Desconectando por canal vacío.")
                queue.clear()
                audio_ready_queue.clear()
                currently_playing = None
                if vc.is_playing() or vc.is_paused():
                    vc.stop()
                await vc.disconnect()
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
                return
        else:
            empty_channel_count = 0

        # Verificar inactividad (30 minutos sin actividad)
        if current_time - last_activity >= 1800:  # 1800 segundos = 30 minutos
            print("[monitor_disconnect] Desconectando por inactividad de 30 minutos.")
            queue.clear()
            audio_ready_queue.clear()
            currently_playing = None
            if vc.is_playing() or vc.is_paused():
                vc.stop()
            await vc.disconnect()
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
            return

        await asyncio.sleep(30)  # Verificar cada 30 segundos

def setup_music_commands(bot):
    @bot.command(name="play")
    @music_channel_only()
    async def play(ctx, *, query: str):
        global queue, queue_messages, processing_task, monitor_task
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
            
            print(f"Añadiendo {len(playlist_tracks)} canciones a la cola...")
            # Procesar solo la primera canción de inmediato
            if playlist_tracks:
                first_track = playlist_tracks[0]
                track_url, track_name, album_image, dur = first_track
                song_info = (track_url, track_name, ctx.author, album_image, dur, False)
                if await process_single_song(ctx, song_info):
                    print(f"Primera canción procesada: {track_name}")
                else:
                    await loading_msg.delete()
                    return await ctx.send(f"No se pudo procesar la primera canción de la playlist '{playlist_name}'. Intenta con otra. 🎵")
            
            # Añadir el resto de las canciones a la cola
            for track in playlist_tracks[1:]:
                track_url, track_name, album_image, dur = track
                queue.append((track_url, track_name, ctx.author, album_image, dur, False))
                print(f"Canción añadida a queue: {track_name}")
            
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
            
            print(f"Añadiendo {len(playlist_tracks)} canciones a la cola desde YouTube...")
            # Procesar solo la primera canción de inmediato
            if playlist_tracks:
                first_track = playlist_tracks[0]
                track_url, track_name, album_image, dur = first_track
                song_info = (track_url, track_name, ctx.author, album_image, dur, True)  # is_youtube_url=True
                if await process_single_song(ctx, song_info):
                    print(f"Primera canción procesada: {track_name}")
                else:
                    await loading_msg.delete()
                    return await ctx.send(f"No se pudo procesar la primera canción de la playlist '{playlist_name}'. Intenta con otra. 🎵")
            
            # Añadir el resto de las canciones a la cola
            for track in playlist_tracks[1:]:
                track_url, track_name, album_image, dur = track
                queue.append((track_url, track_name, ctx.author, album_image, dur, True))  # is_youtube_url=True
                print(f"Canción añadida a queue: {track_name}")
            
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
                track_name, album_image, dur = await run_in_executor(search_spotify, query)
                if track_name:
                    display_name = track_name
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
                print(f"Canción procesada: {display_name}")
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
            print("Comenzando reproducción después de añadir pista...")
            await play_next(ctx)

        # Iniciar o reiniciar el monitoreo de desconexión
        if monitor_task and not monitor_task.done():
            monitor_task.cancel()
        monitor_task = asyncio.create_task(monitor_disconnect(ctx))

    @bot.command()
    @music_channel_only()
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
        
        print(f"Cola después de shuffle (comando): audio_ready_queue={[(item[1], item[4]) for item in audio_ready_queue]}, queue={[(item[1], item[4]) for item in queue]}")
        
        # Procesar la primera canción de inmediato si no hay canciones listas
        if not audio_ready_queue and queue:
            first_song = queue.pop(0)
            if await process_single_song(ctx, first_song):
                print(f"Primera canción después de shuffle procesada: {first_song[1]}")
        
        await ctx.send("🔀 ¡Cola mezclada! Las próximas canciones se reproducirán en orden aleatorio.")
        
        # Iniciar procesamiento en segundo plano para las canciones restantes
        if queue:
            processing_task = asyncio.create_task(process_next_songs(ctx))

        # Reiniciar el monitoreo de desconexión
        if monitor_task and not monitor_task.done():
            monitor_task.cancel()
        monitor_task = asyncio.create_task(monitor_disconnect(ctx))

    @bot.command()
    @music_channel_only()
    async def queue(ctx):
        global queue, audio_ready_queue
        if not audio_ready_queue and not queue:
            return await ctx.send("La cola está vacía. ¡Añade algunas canciones! 🎵")
        
        # Tomar una instantánea de las colas para evitar discrepancias
        current_audio_ready = audio_ready_queue.copy()
        current_queue = queue.copy()
        
        # Depuración: Mostrar el contenido de las colas
        print(f"[queue] audio_ready_queue: {[(item[1], item[4]) for item in current_audio_ready]}")
        print(f"[queue] queue: {[(item[1], item[4]) for item in current_queue]}")
        
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
    @music_channel_only()
    async def leave(ctx):
        global skip_flag, current_message, queue_messages, processing_task, currently_playing, monitor_task
        if ctx.voice_client:
            queue.clear()
            audio_ready_queue.clear()
            currently_playing = None
            if processing_task and not processing_task.done():
                processing_task.cancel()
            if monitor_task and not monitor_task.done():
                monitor_task.cancel()
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

    # Iniciar el monitoreo al conectar
    @bot.event
    async def on_voice_state_update(member, before, after):
        global monitor_task
        if member == bot.user and after.channel and not monitor_task:
            monitor_task = asyncio.create_task(monitor_disconnect(member.guild.voice_client))
