import discord
from discord.ext import commands
from .music import setup_music_commands
from .chat import setup_chat_commands
from freegames import setup_freegames, check_free_games  # Ajustado a importación absoluta

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
        # Configurar los comandos
        setup_music_commands(bot)
        setup_chat_commands(bot)
        try:
            setup_freegames(bot)
            print("setup_freegames ejecutado correctamente")
        except Exception as e:
            print(f"Error al ejecutar setup_freegames: {str(e)}")
        commands_setup_done = True

    activity = discord.Game(name="insultando pendejos")
    await bot.change_presence(activity=activity)
    print(f"Bot conectado como {bot.user}")
    # Iniciar la tarea de juegos gratis
    if not check_free_games.is_running():
        check_free_games.start(bot)
        print("Tarea de juegos gratis iniciada.")
    # Listar todos los comandos registrados
    print("Comandos registrados:")
    for command in bot.commands:
        print(f"- {command.name}")

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        await ctx.send("Comando no encontrado. Usa `-comandos` para ver la lista de comandos disponibles.")
    else:
        print(f"Error en comando: {str(error)}")
