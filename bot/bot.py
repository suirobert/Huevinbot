import discord
from discord.ext import commands
from .music import setup_music_commands
from .chat import setup_chat_commands
import logging

# Configurar el logger
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(name)s: %(message)s')
logger = logging.getLogger('bot')

intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True

bot = commands.Bot(command_prefix='-', intents=intents)

# Variable para asegurarnos de que los comandos solo se registren una vez
commands_setup_done = False

@bot.event
async def on_ready():
    global commands_setup_done
    if not commands_setup_done:
        logger.info("Configurando comandos...")
        try:
            setup_music_commands(bot)
            logger.info("setup_music_commands ejecutado correctamente")
        except Exception as e:
            logger.error(f"Error al ejecutar setup_music_commands: {str(e)}")

        try:
            setup_chat_commands(bot)
            logger.info("setup_chat_commands ejecutado correctamente")
        except Exception as e:
            logger.error(f"Error al ejecutar setup_chat_commands: {str(e)}")

        commands_setup_done = True
        logger.info("Configuración de comandos completada")

    activity = discord.Game(name="insultando pendejos")
    await bot.change_presence(activity=activity)
    logger.info(f"Bot conectado como {bot.user}")

    # Listar todos los comandos registrados
    logger.info("Comandos registrados:")
    for command in bot.commands:
        logger.info(f"- {command.name}")

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        await ctx.send("Comando no encontrado. Usa `-comandos` para ver la lista de comandos disponibles.")
    elif isinstance(error, commands.CheckFailure):
        # No hacer nada: el mensaje ya fue enviado por el chequeo music_channel_only
        logger.info(f"CheckFailure ignorado: {ctx.command.name} usado en canal incorrecto (ID: {ctx.channel.id})")
    else:
        logger.error(f"Error en comando: {str(error)}")
