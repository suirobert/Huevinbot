import discord
import asyncio
import concurrent.futures
import random
from .utils import get_youtube_info, search_spotify, get_spotify_track_info, get_spotify_playlist_info

# Cola y configuraciones
queue = []
skip_flag = False
executor = concurrent.futures.ThreadPoolExecutor(max_workers=2)

# Función para ejecutar tareas pesadas en un hilo separado
async def run_in_executor(func, *args):
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(executor, func, *args)

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
        global skip_flag
        await interaction.response.defer(ephemeral=True)
        vc = self.ctx.voice_client
        if not vc:
            return await interaction.followup.send("No estoy conectado a ningún canal de voz.", ephemeral=True)
        if not queue:
            return await interaction.followup.send("La cola está vacía.", ephemeral=True)
        if vc.is_playing() or vc.is_paused():
            skip_flag = True
            vc.stop()
            await asyncio.sleep(1.0)
        print(f"Estado del voice_client después de stop: is_playing={vc.is_playing()}, is_paused={vc.is_paused()}")
        await play_next(self.ctx)

    @discord.ui.button(label="", emoji="📜", style=discord.ButtonStyle.grey)
    async def show_queue(self, interaction: discord.Interaction, button):
        await interaction.response.defer(ephemeral=True)
        if not queue:
            return await interaction.followup.send("La cola está vacía. ¡Añade algunas canciones! 🎵", ephemeral=True)
        
        embed = discord.Embed(title="📜 Cola de Canciones", color=discord.Color.blue())
        description = ""
        for i, (url_or_query, display_query, requester, album_image, dur, is_youtube_url) in enumerate(queue[:10], 1):
            duration_str = f"[{dur // 60:02d}:{dur % 60:02d}]"
            description += f"**{i}.** {display_query.split(' (')[0].strip()} • {duration_str} (por {requester.mention})\n"
        if len(queue) > 10:
            description += f"\nY {len(queue) - 10} más..."
        embed.description = description
        await interaction.followup.send(embed=embed, ephemeral=True)

    @discord.ui.button(label="", emoji="⏹️", style=discord.ButtonStyle.danger)
    async def stop(self, interaction: discord.Interaction, button):
        global skip_flag
        await interaction.response.defer(ephemeral=True)
        vc = self.ctx.voice_client
        if not vc:
            return await interaction.followup.send("No estoy conectado a ningún canal de voz.", ephemeral=True)
        queue.clear()
        if vc.is_playing() or vc.is_paused():
            skip_flag = True
            vc.stop()
            await asyncio.sleep(1.0)
        await vc.disconnect()
        await interaction.followup.send("Reproducción detenida y desconectado. 🛑", ephemeral=True)
        self.clear_items()

async def play_next(ctx):
    global skip_flag
    if not queue:
        return

    url_or_query, display_query, requester, album_image, dur, is_youtube_url = queue[0]
    vc = ctx.voice_client
    if not vc:
        return

    print(f"Intentando reproducir: {display_query}")
    url, title, thumb, dur_yt, vid_url, uploader = await run_in_executor(get_youtube_info, url_or_query, is_youtube_url)
    if not url:
        print(f"No se pudo obtener el enlace de audio para: {display_query}")
        queue.pop(0)
        await ctx.send("No pude encontrar el video en YouTube, pasando a la siguiente canción...")
        return await play_next(ctx)

    if url.endswith(".m3u8"):
        print(f"Formato no compatible (.m3u8) para: {display_query}")
        queue.pop(0)
        await ctx.send("Formato no compatible (.m3u8), pasando a la siguiente canción...")
        return await play_next(ctx)

    dur = dur if dur else dur_yt

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

        queue.pop(0)
        vc.play(source, after=after)

        embed = discord.Embed(color=discord.Color.blue())
        duration_str = f"[{dur // 60:02d}:{dur % 60:02d}]"
        embed.description = (
            f"**Reproduciendo** 🎶\n"
            f"**{display_query.split(' (')[0].strip()}** • {duration_str}\n"
            f"**Solicitado por:** {requester.mention}\n"
            f"**Canciones en cola:** {len(queue)}"
        )
        if album_image:
            embed.set_thumbnail(url=album_image)
        else:
            embed.set_thumbnail(url=thumb)

        await ctx.send(embed=embed, view=MusicControls(ctx.bot, ctx))

    except Exception as e:
        print(f"Error detallado al reproducir {display_query}: {str(e)}")
        queue.pop(0)
        await ctx.send(f"Hubo un error al reproducir la canción: {str(e)}. Pasando a la siguiente...")
        await play_next(ctx)

def setup_music_commands(bot):
    @bot.command()
    async def play(ctx, *, query: str):
        if ctx.author.voice is None:
            return await ctx.send("Debes estar en un canal de voz para usar este comando. 🎙️")

        loading_msg = await ctx.send("🔄 Buscando y cargando, espera un momento...")

        vc = ctx.voice_client or await ctx.author.voice.channel.connect()
        
        is_youtube_url = "youtube.com/watch?v=" in query or "youtu.be/" in query
        is_spotify_track = "spotify.com/track" in query
        is_spotify_playlist = "spotify.com/playlist" in query
        original_url = query if is_youtube_url else None
        
        if is_spotify_playlist:
            playlist_tracks = await run_in_executor(get_spotify_playlist_info, query)
            if not playlist_tracks:
                await loading_msg.delete()
                return await ctx.send("No pude obtener las canciones de la playlist. Intenta con otra. 🎵")
            
            for track_name, album_image, dur in playlist_tracks:
                queue.append((track_name, track_name, ctx.author, album_image, dur, False))
            
            embed = discord.Embed(color=discord.Color.blue())
            embed.description = (
                f"**Añadidas {len(playlist_tracks)} canciones a la Cola** 🩸\n"
                f"**Queue Length:** {len(queue)}"
            )
            await loading_msg.delete()
            await ctx.send(embed=embed)

        else:
            album_image = None
            dur = 0
            if is_youtube_url:
                url, title, thumb, dur, vid_url, uploader = await run_in_executor(get_youtube_info, query, True)
                if not url:
                    await loading_msg.delete()
                    return await ctx.send("No pude obtener la información del video de YouTube. Intenta con otro enlace. 🎵")
                display_query = title
                track_name, album_image, dur_spotify = await run_in_executor(search_spotify, title)
                if track_name:
                    dur = dur_spotify if dur_spotify else dur
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
                    url, title, thumb, dur, vid_url, uploader = await run_in_executor(get_youtube_info, query, False)
                    if not url:
                        await loading_msg.delete()
                        return await ctx.send("No encontré esa canción en YouTube. Prueba con otra. 🔍")
                    display_query = title

            queue.append((original_url or display_query, display_query, ctx.author, album_image, dur, is_youtube_url))

            duration_str = f"[{dur // 60:02d}:{dur % 60:02d}]"
            embed = discord.Embed(color=discord.Color.blue())
            embed.description = (
                f"**Añadido a la Cola** 🩸\n"
                f"**{display_query.split(' (')[0].strip()}** • {duration_str}\n"
                f"**Queue Length:** {len(queue)}"
            )
            if album_image:
                embed.set_thumbnail(url=album_image)
            await loading_msg.delete()
            await ctx.send(embed=embed)

        if not vc.is_playing() and not vc.is_paused():
            await play_next(ctx)

    @bot.command()
    async def shuffle(ctx):
        if not queue:
            return await ctx.send("La cola está vacía. ¡Añade algunas canciones primero! 🎵")
        
        random.shuffle(queue)
        await ctx.send("🔀 ¡Cola mezclada! Las canciones ahora se reproducirán en orden aleatorio.")

    @bot.command()
    async def leave(ctx):
        global skip_flag
        if ctx.voice_client:
            queue.clear()
            if ctx.voice_client.is_playing() or ctx.voice_client.is_paused():
                skip_flag = True
                ctx.voice_client.stop()
                await asyncio.sleep(1.0)
            await ctx.voice_client.disconnect()
            await ctx.send("👋 Me salí del canal de voz. ¡Nos vemos!")
        else:
            await ctx.send("No estoy en ningún canal de voz. ¿Qué quieres que haga? 🤔")

    @bot.command()
    async def comandos(ctx):
        desc = (
            "**Comandos disponibles:**\n"
            "-play <nombre o enlace>: Busca y reproduce música de YouTube o Spotify (soporta playlists). 🎵\n"
            "-shuffle: Mezcla la cola de canciones para reproducirlas en orden aleatorio. 🔀\n"
            "-leave: Desconecta al bot del canal de voz. 👋\n"
            "-comandos: Muestra esta lista de comandos. 📜\n"
            "-huevin <mensaje>: Habla con Huevín (solo en el canal autorizado y con el rol @Friends). 😈"
        )
        await ctx.send(embed=discord.Embed(description=desc, color=discord.Color.teal()))
