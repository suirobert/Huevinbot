import discord
from discord.ext import commands
import aiohttp
import json

# Configuración del bot
ANILIST_API_URL = "https://graphql.anilist.co"

# Consulta GraphQL para buscar anime
ANIME_QUERY = """
query ($search: String) {
  Media(search: $search, type: ANIME) {
    id
    title {
      romaji
      english
    }
    episodes
    status
    description
    averageScore
    genres
    siteUrl
  }
}
"""

# Consulta GraphQL para buscar manga
MANGA_QUERY = """
query ($search: String) {
  Media(search: $search, type: MANGA) {
    id
    title {
      romaji
      english
    }
    chapters
    volumes
    status
    description
    averageScore
    genres
    siteUrl
  }
}
"""

def setup_anime_commands(bot):
    @bot.command()
    async def anime(ctx, *, search: str):
        """Busca información sobre un anime usando AniList."""
        async with aiohttp.ClientSession() as session:
            # Preparar la consulta GraphQL
            payload = {
                "query": ANIME_QUERY,
                "variables": {"search": search}
            }
            async with session.post(ANILIST_API_URL, json=payload) as response:
                if response.status != 200:
                    return await ctx.send("Error al buscar el anime. Intenta de nuevo más tarde. 😢")
                
                data = await response.json()
                anime = data.get("data", {}).get("Media")
                
                if not anime:
                    return await ctx.send(f"No encontré ningún anime con el nombre '{search}'. Intenta con otro título. 🔍")
                
                # Crear un embed con la información del anime
                embed = discord.Embed(title=anime["title"]["romaji"], url=anime["siteUrl"], color=discord.Color.blue())
                if anime["title"]["english"]:
                    embed.add_field(name="Título en inglés", value=anime["title"]["english"], inline=True)
                embed.add_field(name="Episodios", value=anime["episodes"] or "N/A", inline=True)
                embed.add_field(name="Estado", value=anime["status"].replace("_", " ").title(), inline=True)
                embed.add_field(name="Puntuación", value=f"{anime['averageScore']}/100" if anime["averageScore"] else "N/A", inline=True)
                embed.add_field(name="Géneros", value=", ".join(anime["genres"]) if anime["genres"] else "N/A", inline=False)
                embed.add_field(name="Descripción", value=anime["description"][:200].replace("<br>", "") + "..." if anime["description"] else "Sin descripción", inline=False)
                embed.set_footer(text="Datos proporcionados por AniList")
                await ctx.send(embed=embed)

    @bot.command()
    async def manga(ctx, *, search: str):
        """Busca información sobre un manga usando AniList."""
        async with aiohttp.ClientSession() as session:
            # Preparar la consulta GraphQL
            payload = {
                "query": MANGA_QUERY,
                "variables": {"search": search}
            }
            async with session.post(ANILIST_API_URL, json=payload) as response:
                if response.status != 200:
                    return await ctx.send("Error al buscar el manga. Intenta de nuevo más tarde. 😢")
                
                data = await response.json()
                manga = data.get("data", {}).get("Media")
                
                if not manga:
                    return await ctx.send(f"No encontré ningún manga con el nombre '{search}'. Intenta con otro título. 🔍")
                
                # Crear un embed con la información del manga
                embed = discord.Embed(title=manga["title"]["romaji"], url=manga["siteUrl"], color=discord.Color.green())
                if manga["title"]["english"]:
                    embed.add_field(name="Título en inglés", value=manga["title"]["english"], inline=True)
                embed.add_field(name="Capítulos", value=manga["chapters"] or "N/A", inline=True)
                embed.add_field(name="Volúmenes", value=manga["volumes"] or "N/A", inline=True)
                embed.add_field(name="Estado", value=manga["status"].replace("_", " ").title(), inline=True)
                embed.add_field(name="Puntuación", value=f"{manga['averageScore']}/100" if manga["averageScore"] else "N/A", inline=True)
                embed.add_field(name="Géneros", value=", ".join(manga["genres"]) if manga["genres"] else "N/A", inline=False)
                embed.add_field(name="Descripción", value=manga["description"][:200].replace("<br>", "") + "..." if manga["description"] else "Sin descripción", inline=False)
                embed.set_footer(text="Datos proporcionados por AniList")
                await ctx.send(embed=embed)
