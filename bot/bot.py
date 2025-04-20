import discord
from discord.ext import commands
from .music import setup_music_commands
from .chat import setup_chat_commands
from .freegames import setup_freegames, check_free_games

intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True

bot = commands.Bot(command_prefix='-', intents=intents)

@bot.event
async def on_ready():
    activity = discord.Game(name="insultando pendejos")
    await bot.change_presence(activity=activity)
    print(f"Bot conectado como {bot.user}")
    # Iniciar la tarea de juegos gratis
    if not check_free_games.is_running():
        check_free_games.start(bot)
        print("Tarea de juegos gratis iniciada.")

# Configurar los comandos
def setup():
    setup_music_commands(bot)
    setup_chat_commands(bot)
    setup_freegames(bot)

# Ejecutar la configuración
setup()
