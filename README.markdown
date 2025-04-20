# HuevínBot 🎶😈

HuevínBot es un bot de Discord diseñado para reproducir música de YouTube y Spotify, buscar información sobre anime y manga, responder con humor negro y sarcasmo usando ChatGPT (bajo ciertas restricciones), y ofrecer herramientas de moderación para gestionar el servidor. Este bot combina funcionalidades de entretenimiento con herramientas administrativas, optimizando el uso de recursos como los tokens de la API de ChatGPT.

## Características principales

- **Reproducción de música**: Reproduce canciones y playlists de YouTube y Spotify con comandos intuitivos.
- **Gestión de cola**: Mezcla la cola, salta canciones, y muestra la lista de reproducción.
- **Búsqueda de anime y manga**: Busca información detallada sobre anime y manga usando la API de AniList.
- **Interacción con ChatGPT**: Responde con humor negro y sarcasmo usando el comando `-huevin` (restringido a usuarios con el rol "Friends" y a un canal específico).
- **Moderación del servidor**: Comandos para banear, expulsar, silenciar, borrar mensajes, y asignar roles.
- **Optimización**: Procesamiento eficiente de canciones y consumo controlado de tokens de ChatGPT.

## Requisitos

- Python 3.8+
- Discord.py (`pip install discord.py`)
- FFmpeg (para reproducción de audio, asegúrate de que esté instalado y accesible en tu sistema)
- OpenAI API (`pip install openai`) para las respuestas de ChatGPT
- Dependencias adicionales:
  - `yt-dlp` (`pip install yt-dlp`) para descargar audio de YouTube
  - `aiohttp` (`pip install aiohttp`) para solicitudes HTTP a la API de AniList
  - Otras dependencias listadas en `requirements.txt`

## Instalación

1. **Clona el repositorio**:

   ```bash
   git clone <URL-del-repositorio>
   cd huevinbot
   ```

2. **Instala las dependencias**:

   ```bash
   pip install -r requirements.txt
   ```

3. **Configura las variables de entorno**:

   - Crea un archivo `config.py` en el directorio `bot/` con las siguientes variables:

     ```python
     # Token de Discord (obténlo desde el portal de desarrolladores de Discord)
     DISCORD_TOKEN = "tu-token-de-discord"
     
     # ID del servidor de Discord donde se usará el bot
     GUILD_ID = 123456789
     
     # Clave de API de OpenAI (para ChatGPT)
     OPENAI_API_KEY = "tu-clave-de-openai"
     
     # ID del canal donde se permite usar el comando -huevin
     ALLOWED_CHANNEL_ID = 123456789
     
     # ID del rol "Friends" para restringir el uso de -huevin
     ALLOWED_ROLE_ID = 123456789
     
     # Tiempo de inactividad antes de borrar el historial de conversación (en segundos)
     CONVERSATION_TIMEOUT = 3600  # 1 hora
     
     # Máximo número de mensajes en el historial de conversación por usuario
     MAX_HISTORY = 5
     ```

4. **Asegúrate de que FFmpeg esté instalado**:

   - En Linux:

     ```bash
     sudo apt-get install ffmpeg
     ```

   - En Windows: Descarga FFmpeg desde su sitio oficial y añádelo al PATH.

5. **Ejecuta el bot**:

   ```bash
   python bot/main.py
   ```

## Comandos disponibles

### Comandos de música 🎵

- `-play <nombre o enlace>`\
  Busca y reproduce una canción o playlist de YouTube o Spotify. Soporta enlaces directos y búsquedas por nombre.\
  Ejemplo: `-play Sabrina Carpenter - Please Please Please`\
  Ejemplo con playlist: `-play https://www.youtube.com/playlist?list=OLAK5uy_mVMKdwsPUdw2ZGiBMeTxtQD5Bl0Hr5nbM`

- `-shuffle`\
  Mezcla la cola de canciones para reproducirlas en orden aleatorio.\
  Ejemplo: `-shuffle`

- `-queue`\
  Muestra la cola de canciones actual (hasta 10 canciones, con el resto resumido).\
  Ejemplo: `-queue`

- `-leave`\
  Desconecta al bot del canal de voz y limpia la cola.\
  Ejemplo: `-leave`

### Comandos de anime y manga 📺📚

- `-anime <nombre>`\
  Busca información sobre un anime usando la API de AniList (título, episodios, estado, puntuación, géneros, descripción).\
  Ejemplo: `-anime Jujutsu Kaisen`

- `-manga <nombre>`\
  Busca información sobre un manga usando la API de AniList (título, capítulos, volúmenes, estado, puntuación, géneros, descripción).\
  Ejemplo: `-manga One Piece`

### Comandos de interacción 😈

- `-huevin <mensaje>`\
  Habla con Huevín, quien responde con humor negro y sarcasmo.\
  **Restricciones**: Solo usuarios con el rol @Friends pueden usar este comando, y solo en el canal autorizado.\
  Ejemplo: `-huevin ¿Qué opinas de mi nuevo corte de cabello?`

- `-comandos`\
  Muestra la lista de comandos disponibles.\
  Ejemplo: `-comandos`

### Comandos de moderación 🔧

- `-ban <usuario> [razón]`\
  Banea a un usuario del servidor. Requiere permisos de moderación.\
  Ejemplo: `-ban @Juanito Spam`

- `-unban <user_id> [razón]`\
  Desbanea a un usuario usando su ID. Requiere permisos de moderación.\
  Ejemplo: `-unban 123456789 Amnistía`

- `-kick <usuario> [razón]`\
  Expulsa a un usuario del servidor. Requiere permisos de moderación.\
  Ejemplo: `-kick @Juanito Comportamiento inapropiado`

- `-mute <usuario> <duración_en_minutos> [razón]`\
  Silencia a un usuario por un tiempo específico (en minutos). Requiere permisos de moderación.\
  Ejemplo: `-mute @Juanito 10 Hablar demasiado`

- `-clear <cantidad>`\
  Borra una cantidad específica de mensajes en el canal (máximo 100). Requiere permisos de moderación.\
  Ejemplo: `-clear 50`

- `-role <usuario> <rol>`\
  Asigna un rol a un usuario. Requiere permisos de moderación.\
  Ejemplo: `-role @Juanito @Gamer`

### Interfaz de reproducción 🎶

Cuando se reproduce una canción, se muestra un mensaje con controles interactivos:

- ⏯️: Pausar/Reanudar la reproducción.
- ⏭️: Saltar a la siguiente canción.
- 🔀: Mezclar la cola.
- 📜: Mostrar la cola de canciones.
- ⏹️: Detener la reproducción y desconectar al bot.

## Notas sobre el uso de ChatGPT

- **Restricción de uso**: El comando `-huevin` es el único que utiliza la API de ChatGPT. Está restringido a:
  - Usuarios con el rol "Friends".
  - Un canal específico definido en `ALLOWED_CHANNEL_ID`.
- **Consumo de tokens**:
  - Solo las respuestas generadas por `-huevin` consumen tokens de ChatGPT.
  - Se limita a `max_tokens=75` por respuesta para minimizar el uso.
  - El historial de conversación por usuario está limitado a `MAX_HISTORY` mensajes, y las conversaciones inactivas se eliminan después de `CONVERSATION_TIMEOUT` segundos.
- **Otros comandos**: Ningún otro comando o mensaje del bot (como `-play`, `-queue`, o mensajes de error) consume tokens de ChatGPT.

## Estructura del proyecto

- `bot/main.py`: Archivo principal que inicializa el bot y carga los comandos.
- `bot/music.py`: Comandos y lógica para la reproducción de música.
- `bot/chat.py`: Comandos y lógica para la interacción con ChatGPT.
- `bot/anime.py`: Comandos para buscar información de anime y manga usando la API de AniList.
- `bot/moderation.py`: Comandos de moderación para gestionar el servidor.
- `bot/utils.py`: Funciones auxiliares para interactuar con YouTube y Spotify.
- `bot/config.py`: Archivo de configuración con tokens y variables de entorno.

## Despliegue en Railway

1. Sube el proyecto a un repositorio de GitHub.
2. Conecta Railway a tu repositorio.
3. Configura las variables de entorno en Railway (`DISCORD_TOKEN`, `OPENAI_API_KEY`, etc.).
4. Despliega el proyecto y verifica los logs para asegurarte de que el bot se conecte correctamente.

## Contribuciones

Si quieres añadir nuevas funcionalidades o reportar errores, abre un issue o envía un pull request en el repositorio.

## Licencia

Este proyecto está bajo la licencia MIT. Siéntete libre de usarlo y modificarlo como desees.

---

**¡Disfruta de HuevínBot! 🎶😈**