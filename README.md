Huevin Music Bot
Un bot de Discord multifuncional que reproduce música desde YouTube y Spotify, con controles interactivos y una función de chat con humor negro y sarcasmo. 🎶😈
Descripción
Huevin Music Bot es un bot de Discord diseñado para reproducir música desde enlaces de YouTube y Spotify o mediante búsquedas por nombre de canción. Incluye controles interactivos para pausar, saltar o detener la reproducción, y una función adicional (-huevin) que permite interactuar con un asistente de chat con humor negro y sarcasmo (restringido a usuarios con un rol específico en un canal autorizado).
Características

Reproducción de música: Reproduce canciones desde enlaces de YouTube, Spotify o mediante búsqueda por nombre.
Carátulas de Spotify: Muestra la carátula del álbum obtenida desde Spotify para una mejor presentación visual.
Cola de canciones: Gestiona una cola de reproducción con información sobre las canciones en espera.
Controles interactivos: Incluye botones para pausar/reanudar, saltar a la siguiente canción o detener la reproducción.
Chat con humor negro: Usa el comando -huevin para interactuar con un asistente que responde con sarcasmo (restringido a usuarios con el rol @Friends en un canal específico).
Mensajes personalizados: Embeds visuales para mostrar información de las canciones, con colores y emojis.

Requisitos

Python 3.8 o superior
Una cuenta de Discord y un bot creado en el Discord Developer Portal
Credenciales de Spotify (Client ID y Client Secret) desde el Spotify Developer Dashboard
Una clave de API de OpenAI para la función de chat (opcional, solo si usas -huevin)
FFmpeg instalado en tu sistema para la reproducción de audio

Dependencias de Python
Instala las dependencias necesarias con:
pip install discord.py spotipy yt-dlp python-dotenv openai

Instalación

Clona el repositorio:
git clone https://github.com/suirobert/huevin-music-bot.git
cd huevin-music-bot


Configura las variables de entorno:Crea un archivo .env en la raíz del proyecto y añade las siguientes variables:
DISCORD_TOKEN=tu-token-de-discord
SPOTIFY_CLIENT_ID=tu-spotify-client-id
SPOTIFY_CLIENT_SECRET=tu-spotify-client-secret
OPENAI_API_KEY=tu-openai-api-key


Instala FFmpeg:

En Ubuntu/Debian:sudo apt-get install ffmpeg


En Windows: Descarga FFmpeg desde su sitio oficial y añádelo al PATH.
En macOS (con Homebrew):brew install ffmpeg




Ejecuta el bot:
python music_bot_fixed_v3.py



Uso

Invita el bot a tu servidor de Discord usando el enlace generado en el Discord Developer Portal.

Usa los siguientes comandos:

-play <nombre o enlace>: Reproduce una canción desde un enlace de YouTube/Spotify o busca por nombre.Ejemplo: -play https://www.youtube.com/watch?v=suAR1PYFNYA o -play Houdini Dua Lipa
-leave: Desconecta el bot del canal de voz.
-comandos: Muestra la lista de comandos disponibles.
-huevin <mensaje>: Interactúa con el asistente de chat con humor negro (solo en el canal autorizado y con el rol @Friends).Ejemplo: -huevin ¿por qué eres tan lento?


Usa los botones interactivos en los embeds de reproducción para controlar la música (⏯️ para pausar/reanudar, ⏭️ para saltar, ⏹️ para detener).


Configuración adicional

Canal y rol para -huevin: Asegúrate de configurar el ALLOWED_CHANNEL_ID y ALLOWED_ROLE_ID en el código para restringir el uso del comando -huevin.
FFmpeg: Si el bot no reproduce audio, verifica que FFmpeg esté correctamente instalado y accesible en el PATH.

Contribución
¡Las contribuciones son bienvenidas! Si deseas contribuir:

Haz un fork del repositorio.
Crea una nueva rama (git checkout -b feature/nueva-funcionalidad).
Realiza tus cambios y haz commit (git commit -m "Añade nueva funcionalidad").
Sube tus cambios (git push origin feature/nueva-funcionalidad).
Abre un Pull Request.

Licencia
Este proyecto está bajo la Licencia MIT. Consulta el archivo LICENSE para más detalles.
Contacto
Si tienes preguntas o problemas, abre un issue en el repositorio o contáctame en Discord: @inge robert.
