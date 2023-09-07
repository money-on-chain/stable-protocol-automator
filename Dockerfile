FROM python:3.10

# Autor
LABEL maintainer='martin.mulone@moneyonchain.com'

RUN apt-get update && \
    apt-get install -y \
        locales

RUN echo $TZ > /etc/timezone && \
    apt-get update && apt-get install -y tzdata && \
    rm /etc/localtime && \
    ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && \
    dpkg-reconfigure -f noninteractive tzdata && \
    apt-get clean

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt


RUN mkdir /home/www-data && mkdir /home/www-data/app \
    && mkdir /home/www-data/app/moc_jobs

ARG CONFIG=config.json

WORKDIR /home/www-data/app/moc_jobs/
COPY app_run_automator.py ./
ADD $CONFIG ./config.json
COPY moc_jobs/ ./moc_jobs/
ENV PATH "$PATH:/home/www-data/app/moc_jobs/"
ENV AWS_DEFAULT_REGION=us-west-1
ENV PYTHONPATH "${PYTONPATH}:/home/www-data/app/moc_jobs/"

CMD ["python", "./app_run_automator.py"]
