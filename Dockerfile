FROM python:3.9.12-slim-buster
RUN apt-get update && apt-get install -y libmagic1 ffmpeg
RUN pip install -r requirements.txt
WORKDIR AudioBridge/
COPY ./AudioBridge/ .
CMD ["python3", "audioBridge.py"]

