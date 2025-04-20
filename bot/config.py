import os
from datetime import timedelta

# Cargar variables de entorno
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = int(os.getenv("GUILD_ID", 0))
SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ALLOWED_CHANNEL_ID = int(os.getenv("ALLOWED_CHANNEL_ID", 0))
ALLOWED_ROLE_ID = int(os.getenv("ALLOWED_ROLE_ID", 0))
CONVERSATION_TIMEOUT = timedelta(minutes=int(os.getenv("CONVERSATION_TIMEOUT_MINUTES", 30)))
MAX_HISTORY = int(os.getenv("MAX_HISTORY", 3))

# Validar variables requeridas
if not DISCORD_TOKEN:
    raise ValueError("DISCORD_TOKEN no está definido en las variables de entorno.")
if not GUILD_ID:
    raise ValueError("GUILD_ID no está definido en las variables de entorno.")
if not SPOTIFY_CLIENT_ID:
    raise ValueError("SPOTIFY_CLIENT_ID no está definido en las variables de entorno.")
if not SPOTIFY_CLIENT_SECRET:
    raise ValueError("SPOTIFY_CLIENT_SECRET no está definido en las variables de entorno.")
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY no está definido en las variables de entorno.")
if not ALLOWED_CHANNEL_ID:
    raise ValueError("ALLOWED_CHANNEL_ID no está definido en las variables de entorno.")
if not ALLOWED_ROLE_ID:
    raise ValueError("ALLOWED_ROLE_ID no está definido en las variables de entorno.")
