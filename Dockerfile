FROM python:3.9.12-slim-buster
#
WORKDIR AudioBridge/
COPY . .
#
RUN apt-get update
RUN apt-get install -y libmagic1 ffmpeg
#RUN /usr/local/bin/python -m pip install --upgrade pip
RUN pip install -r requirements.txt
#
CMD ["python3", "src/audioBridge.py"]

