import discord
from discord.ext import commands
from .music import setup_music_commands
from .chat import setup_chat_commands

intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True

bot = commands.Bot(command_prefix='-', intents=intents)

@bot.event
async def on_ready():
    activity = discord.Game(name="insultando pendejos")
    await bot.change_presence(activity=activity)
    print(f"Bot conectado como {bot.user}")

# Configurar los comandos
def setup():
    setup_music_commands(bot)
    setup_chat_commands(bot)

# Ejecutar la configuración
setup()
