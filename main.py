import discord
from discord.ext import commands
from bot.config import DISCORD_TOKEN, GUILD_ID
from bot.music import setup_music_commands
from bot.chat import setup_chat_commands
from bot.anime import setup_anime_commands
from bot.moderation import setup_moderation_commands

# Configuración del bot
intents = discord.Intents.default()
intents.message_content = True
intents.members = True  # Necesario para comandos de moderación
bot = commands.Bot(command_prefix="-", intents=intents)

@bot.event
async def on_ready():
    print(f"Bot conectado como {bot.user}")
    try:
        guild = discord.Object(id=GUILD_ID)
        bot.tree.copy_global_to(guild=guild)
        synced = await bot.tree.sync(guild=guild)
        print(f"Comandos sincronizados: {len(synced)}")
    except Exception as e:
        print(f"Error al sincronizar comandos: {e}")

# Cargar los comandos de los módulos
setup_music_commands(bot)
setup_chat_commands(bot)
setup_anime_commands(bot)
setup_moderation_commands(bot)

# Iniciar el bot
bot.run(DISCORD_TOKEN)
