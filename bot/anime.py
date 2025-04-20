import discord
from discord.ext import commands
import aiohttp

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
    coverImage {
      large
    }
    externalLinks {
      site
      url
    }
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
    coverImage {
      large
    }
    externalLinks {
      site
      url
    }
  }
}
"""

# Vista con botones para AniList y plataformas externas
class LinkView(discord.ui.View):
    def __init__(self, anilist_url: str, external_url: str = None, external_label: str = "Ver en Plataforma"):
        super().__init__()
        self.add_item(discord.ui.Button(label="Ver en AniList", url=anilist_url))
        if external_url:
            self.add_item(discord.ui.Button(label=external_label, url=external_url))

def setup_anime_commands(bot):
    @bot.command()
    async def anime(ctx, *, search: str):
        """Busca información sobre un anime usando AniList."""
        async with aiohttp.ClientSession() as session:
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
                
                embed = discord.Embed(title=anime["title"]["romaji"], url=anime["siteUrl"], color=discord.Color.blue())
                if anime["title"]["english"]:
                    embed.add_field(name="Título en inglés", value=anime["title"]["english"], inline=True)
                embed.add_field(name="Episodios", value=anime["episodes"] or "N/A", inline=True)
                embed.add_field(name="Estado", value=anime["status"].replace("_", " ").title(), inline=True)
                embed.add_field(name="Puntuación", value=f"{anime['averageScore']}/100" if anime["averageScore"] else "N/A", inline=True)
                embed.add_field(name="Géneros", value=", ".join(anime["genres"]) if anime["genres"] else "N/A", inline=False)
                embed.add_field(name="Descripción", value=anime["description"][:200].replace("<br>", "") + "..." if anime["description"] else "Sin descripción", inline=False)
                embed.set_thumbnail(url=anime["coverImage"]["large"])
                embed.set_footer(text="Datos proporcionados por AniList")

                # Buscar una plataforma de streaming
                streaming_url = None
                for link in anime.get("externalLinks", []):
                    if link["site"].lower() in ["crunchyroll", "netflix", "hidive", "funimation"]:
                        streaming_url = link["url"]
                        break

                view = LinkView(anilist_url=anime["siteUrl"], external_url=streaming_url, external_label="Ver en Plataforma")
                await ctx.send(embed=embed, view=view)

    @bot.command()
    async def manga(ctx, *, search: str):
        """Busca información sobre un manga usando AniList."""
        async with aiohttp.ClientSession() as session:
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
                
                embed = discord.Embed(title=manga["title"]["romaji"], url=manga["siteUrl"], color=discord.Color.green())
                if manga["title"]["english"]:
                    embed.add_field(name="Título en inglés", value=manga["title"]["english"], inline=True)
                embed.add_field(name="Capítulos", value=manga["chapters"] or "N/A", inline=True)
                embed.add_field(name="Volúmenes", value=manga["volumes"] or "N/A", inline=True)
                embed.add_field(name="Estado", value=manga["status"].replace("_", " ").title(), inline=True)
                embed.add_field(name="Puntuación", value=f"{manga['averageScore']}/100" if manga["averageScore"] else "N/A", inline=True)
                embed.add_field(name="Géneros", value=", ".join(manga["genres"]) if manga["genres"] else "N/A", inline=False)
                embed.add_field(name="Descripción", value=manga["description"][:200].replace("<br>", "") + "..." if manga["description"] else "Sin descripción", inline=False)
                embed.set_thumbnail(url=manga["coverImage"]["large"])
                embed.set_footer(text="Datos proporcionados por AniList")

                # Buscar una plataforma externa para lectura
                external_url = None
                external_label = None
                for link in manga.get("externalLinks", []):
                    if link["site"].lower() in ["bookwalker", "amazon", "manga plus"]:
                        external_url = link["url"]
                        external_label = f"Leer en {link['site']}"
                        break

                view = LinkView(anilist_url=manga["siteUrl"], external_url=external_url, external_label=external_label or "Ver Plataforma")
                await ctx.send(embed=embed, view=view)
