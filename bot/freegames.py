import discord
from discord.ext import commands, tasks
import aiohttp
import json
import os

# Archivo para almacenar juegos ya notificados
GAMES_FILE = "notified_games.json"

def setup_freegames(bot):
    # Cargar juegos ya notificados
    if os.path.exists(GAMES_FILE):
        with open(GAMES_FILE, "r") as f:
            notified_games = json.load(f)
    else:
        notified_games = []

    @tasks.loop(hours=1)  # Verificar cada hora
    async def check_free_games():
        # Obtener el canal donde enviar las notificaciones
        channel = discord.utils.get(bot.get_all_channels(), name="juegos-gratis")
        if not channel:
            print("No se encontró el canal #juegos-gratis. Asegúrate de que exista.")
            return

        # Obtener juegos gratis de la API de GamerPower
        async with aiohttp.ClientSession() as session:
            async with session.get("https://www.gamerpower.com/api/giveaways?sort-by=popularity") as resp:
                if resp.status != 200:
                    print(f"Error al obtener juegos gratis: {resp.status}")
                    return
                games = await resp.json()

        # Filtrar juegos que estén gratis
        new_games = []
        for game in games:
            if game["type"] in ["Game", "DLC"] and game["worth"] != "N/A" and game["open_giveaway_url"]:
                game_id = game["id"]
                if str(game_id) not in notified_games:  # Evitar duplicados
                    notified_games.append(str(game_id))
                    new_games.append(game)

        # Guardar juegos notificados
        with open(GAMES_FILE, "w") as f:
            json.dump(notified_games, f)

        # Enviar notificaciones para cada juego nuevo
        for game in new_games:
            title = game["title"]
            worth = game["worth"]
            description = game["description"]
            platform = ", ".join(game["platforms"].split(", "))
            url = game["open_giveaway_url"]
            image = game.get("image", None)

            embed = discord.Embed(title=title, url=url, color=discord.Color.green())
            embed.add_field(name="Precio Original", value=worth, inline=True)
            embed.add_field(name="Plataforma", value=platform, inline=True)
            embed.add_field(name="Descripción", value=description[:1024], inline=False)  # Limitar a 1024 caracteres
            if image:
                embed.set_thumbnail(url=image)
            embed.set_footer(text="Juego gratis detectado por el bot")
            
            try:
                await channel.send(embed=embed)
            except discord.Forbidden:
                print(f"No tengo permisos para enviar mensajes en el canal #juegos-gratis.")

    @bot.event
    async def on_ready():
        if not check_free_games.is_running():
            check_free_games.start()
            print("Tarea de juegos gratis iniciada.")

    @bot.command()
    async def freegames(ctx):
        """Muestra los juegos gratis disponibles actualmente."""
        async with aiohttp.ClientSession() as session:
            async with session.get("https://www.gamerpower.com/api/giveaways?sort-by=popularity") as resp:
                if resp.status != 200:
                    await ctx.send("No pude obtener la lista de juegos gratis en este momento. Intenta de nuevo más tarde.")
                    return
                games = await resp.json()

        free_games = [game for game in games if game["type"] in ["Game", "DLC"] and game["worth"] != "N/A"]
        if not free_games:
            await ctx.send("No hay juegos gratis disponibles en este momento.")
            return

        embeds = []
        for game in free_games[:5]:  # Limitar a 5 juegos para evitar spam
            embed = discord.Embed(title=game["title"], url=game["open_giveaway_url"], color=discord.Color.green())
            embed.add_field(name="Precio Original", value=game["worth"], inline=True)
            embed.add_field(name="Plataforma", value=", ".join(game["platforms"].split(", ")), inline=True)
            embed.add_field(name="Descripción", value=game["description"][:1024], inline=False)
            if game.get("image"):
                embed.set_thumbnail(url=game["image"])
            embeds.append(embed)

        for embed in embeds:
            await ctx.send(embed=embed)
