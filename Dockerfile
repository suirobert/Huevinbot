FROM python:3.9-slim
WORKDIR /app
COPY . .
RUN apt-get update && apt-get install -y ffmpeg
RUN pip install -r requirements.txt
CMD ["python", "main.py"]
