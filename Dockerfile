FROM python:3.9.12-slim-buster
#
RUN apt-get update
RUN apt-get install -y libmagic1 ffmpeg
#
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
#
WORKDIR /AudioBridge/bin
COPY . /AudioBridge/bin
#
RUN pip install -r requirements.txt
#
ENTRYPOINT ["python3", "-Bu", "src/audioBridge.py"]
