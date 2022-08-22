FROM python:3.9.12-slim-buster
#
RUN apt-get update
RUN apt-get install -y libmagic1 ffmpeg
#
WORKDIR /AudioBridge
COPY . .
#
RUN pip install -r requirements.txt
#
EXPOSE 5432
#
ENTRYPOINT ["python3", "src/audioBridge.py"]
