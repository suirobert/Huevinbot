import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
from bot.music import setup_music_commands
# Importa otros módulos según sea necesario

load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="-", intents=intents)

@bot.event
async def on_ready():
    print(f"Bot conectado como {bot.user}")
    # Establecer la actividad del bot
    activity = discord.Activity(type=discord.ActivityType.playing, name="insultando pendejos")
    await bot.change_presence(activity=activity)

# Configurar comandos de música
setup_music_commands(bot)

# Configurar otros módulos según sea necesario
# Por ejemplo:
# from bot.moderation import setup_moderation_commands
# setup_moderation_commands(bot)

bot.run(DISCORD_TOKEN)
