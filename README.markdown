# 🎵 Huevin Music Bot 🎵

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![Discord](https://img.shields.io/badge/Discord-Bot-green.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

**Un bot de Discord que combina música y humor negro.**  
Reproduce canciones desde YouTube y Spotify, con controles interactivos, y responde con sarcasmo y humor negro en un canal autorizado. 🎶😈

---

## 🚀 **Descripción**

**Huevin Music Bot** es un bot de Discord diseñado para mejorar tu experiencia en servidores. Reproduce música desde enlaces de YouTube o Spotify, o busca canciones por nombre. Incluye botones interactivos para controlar la reproducción y una función de chat con humor negro y sarcasmo (restringida a usuarios con un rol específico). ¡Perfecto para animar tus canales de voz y texto!

---

## ✨ **Características**

- 🎸 **Reproducción de música**: Usa enlaces de YouTube, Spotify o busca por nombre (ej. `-play Houdini Dua Lipa`).
- 🖼️ **Carátulas de Spotify**: Muestra la carátula del álbum para un toque visual elegante.
- 📜 **Cola de canciones**: Gestiona una cola y muestra cuántas canciones están en espera.
- 🕹️ **Controles interactivos**: Botones para pausar/reanudar (⏯️), saltar (⏭️) o detener (⏹️) la música.
- 😈 **Chat con humor negro**: Usa `-huevin` para respuestas sarcásticas (solo para usuarios con el rol `@Friends` en un canal específico).
- 💬 **Mensajes estilizados**: Embeds visuales con información clara y emojis.

---

## 📋 **Requisitos**

- 🐍 **Python 3.8+**
- 🤖 **Cuenta de Discord** y un bot creado en el [Discord Developer Portal](https://discord.com/developers/applications)
- 🎧 **Credenciales de Spotify** (Client ID y Client Secret) desde el [Spotify Developer Dashboard](https://developer.spotify.com/dashboard/)
- 🗣️ **Clave de API de OpenAI** (opcional, solo para la función `-huevin`)
- 🎙️ **FFmpeg** instalado para reproducir audio

### **Dependencias de Python**

Instala las dependencias con:

```bash
pip install discord.py spotipy yt-dlp python-dotenv openai
```

---

## 🛠️ **Instalación**

1. **Clona el repositorio** 📂  
   ```bash
   git clone https://github.com/tu-usuario/huevin-music-bot.git
   cd huevin-music-bot
   ```

2. **Configura las variables de entorno** 🔧  
   Crea un archivo `.env` en la raíz del proyecto y añade:

   ```env
   DISCORD_TOKEN=tu-token-de-discord
   SPOTIFY_CLIENT_ID=tu-spotify-client-id
   SPOTIFY_CLIENT_SECRET=tu-spotify-client-secret
   OPENAI_API_KEY=tu-openai-api-key
   ```

3. **Instala FFmpeg** 🎵  
   - **Ubuntu/Debian**:
     ```bash
     sudo apt-get install ffmpeg
     ```
   - **Windows**: Descarga FFmpeg desde [su sitio oficial](https://ffmpeg.org/download.html) y añádelo al PATH.
   - **macOS** (con Homebrew):
     ```bash
     brew install ffmpeg
     ```

4. **Ejecuta el bot** 🚀  
   ```bash
   python music_bot_fixed_v3.py
   ```

---

## 🎮 **Uso**

1. Invita el bot a tu servidor de Discord usando el enlace generado en el Discord Developer Portal.
2. Usa los siguientes comandos:

   | Comando               | Descripción                                                                 |
   |-----------------------|-----------------------------------------------------------------------------|
   | `-play <nombre o enlace>` | Reproduce una canción desde YouTube, Spotify o busca por nombre.         |
   | `-leave`              | Desconecta el bot del canal de voz.                                       |
   | `-comandos`           | Muestra la lista de comandos disponibles.                                |
   | `-huevin <mensaje>`   | Interactúa con un asistente sarcástico (solo en canal autorizado).       |

   **Ejemplos**:
   - `-play https://www.youtube.com/watch?v=suAR1PYFNYA`  
   - `-play Houdini Dua Lipa`  
   - `-huevin ¿por qué eres tan lento?`

3. Usa los botones interactivos en los embeds para controlar la música:
   - ⏯️ Pausar/Reanudar  
   - ⏭️ Saltar canción  
   - ⏹️ Detener y desconectar

---

## ⚙️ **Configuración adicional**

- **Canal y rol para `-huevin`**: Configura `ALLOWED_CHANNEL_ID` y `ALLOWED_ROLE_ID` en el código para restringir el comando `-huevin`.
- **FFmpeg**: Si el bot no reproduce audio, verifica que FFmpeg esté instalado y accesible en el PATH.

---

## 🤝 **Contribución**

¡Las contribuciones son bienvenidas! Sigue estos pasos:

1. Haz un fork del repositorio 🍴
2. Crea una nueva rama (`git checkout -b feature/nueva-funcionalidad`)
3. Realiza tus cambios y haz commit (`git commit -m "Añade nueva funcionalidad"`)
4. Sube tus cambios (`git push origin feature/nueva-funcionalidad`)
5. Abre un Pull Request 📬

---

## 📜 **Licencia**

Este proyecto está bajo la **Licencia MIT**. Consulta el archivo [LICENSE](LICENSE) para más detalles.

---

## 📧 **Contacto**

Si tienes preguntas o problemas, abre un issue en el repositorio o contáctame en Discord: `tu-usuario#1234`.

---

**¡Disfruta de la música y el humor negro con Huevin Music Bot!** 🎉