import os
from dotenv import load_dotenv
from datetime import timedelta

load_dotenv()

# Configuración de Spotify
SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")

# Configuración de OpenAI
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Configuraciones del bot
ALLOWED_CHANNEL_ID = 1108528856408805417
ALLOWED_ROLE_ID = 714948180617330728
CONVERSATION_TIMEOUT = timedelta(minutes=30)
MAX_HISTORY = 3
