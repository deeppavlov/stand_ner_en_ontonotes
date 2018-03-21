FROM stand/docker_cuda

VOLUME /vol
WORKDIR /app
ADD . /app

RUN pip install -r requirements.txt && \
    ./download_components.sh

EXPOSE 6006

CMD python3.6 ner_en_api.py > /vol/ner_en.log 2>&1