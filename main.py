import discord
from discord.ext import commands
from bot.config import DISCORD_TOKEN, GUILD_ID
from bot.music import setup_music_commands
from bot.chat import setup_chat_commands
from bot.anime import setup_anime_commands
from bot.moderation import setup_moderation_commands

# Configuración del bot
print("Inicializando intents...")
intents = discord.Intents.default()
intents.message_content = True
intents.members = True  # Necesario para comandos de moderación
print("Creando instancia del bot...")
bot = commands.Bot(command_prefix="-", intents=intents)

@bot.event
async def on_ready():
    print(f"Bot conectado como {bot.user}")
    try:
        activity = discord.Game(name="insultando pendejos")
        await bot.change_presence(activity=activity)
        guild = discord.Object(id=GUILD_ID)
        bot.tree.copy_global_to(guild=guild)
        synced = await bot.tree.sync(guild=guild)
        print(f"Comandos sincronizados: {len(synced)}")
    except Exception as e:
        print(f"Error al sincronizar comandos: {e}")

# Cargar los comandos de los módulos
print("Cargando módulo music...")
setup_music_commands(bot)
print("Cargando módulo chat...")
setup_chat_commands(bot)
print("Cargando módulo anime...")
setup_anime_commands(bot)
print("Cargando módulo moderation...")
setup_moderation_commands(bot)

# Iniciar el bot
print("Iniciando el bot...")
try:
    bot.run(DISCORD_TOKEN)
except Exception as e:
    print(f"Error al iniciar el bot: {e}")
