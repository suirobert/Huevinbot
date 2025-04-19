import os
from dotenv import load_dotenv
from bot.bot import bot

load_dotenv()

# Ejecutar el bot
bot.run(os.getenv("DISCORD_TOKEN"))
