FROM python:3.9.12-slim-buster

RUN apt-get update
RUN apt-get install -y libmagic1 ffmpeg
RUN apt-get install -y pandoc

WORKDIR /AudioBridge/bin

COPY ./requirements.txt /AudioBridge/bin/requirements.txt
RUN pip install -r requirements.txt

COPY . /AudioBridge/bin

ENTRYPOINT ["python3", "-Bu", "-m", "audiobridge"]
