FROM python:3.12.3-slim
LABEL maintainer="Jacques SOUDE <bostersoude@gmail.com>"
ENV PYTHONUNBUFFERED 1
ENV PYTHONDONTWRITEBYTECODE 1

# create the appropriate directories
ENV HOME=/home/app
ENV APP_HOME=/home/app/web
RUN mkdir -p $APP_HOME/static
RUN mkdir -p $APP_HOME/media
# Créer les sous-répertoires nécessaires pour les médias
RUN mkdir -p $APP_HOME/media/deceased_images \
    && mkdir -p $APP_HOME/media/custom_book_covers \
    && mkdir -p $APP_HOME/media/book_purchase_pdfs

WORKDIR $APP_HOME

RUN mkdir -p $HOME/.cache/pip

# install psycopg Pillow psycopg2 dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
    libjpeg-dev zlib1g-dev libmemcached-dev libpq-dev gcc python3-dev libssl-dev rsync \
    libglib2.0-0 libpango-1.0-0 libpangocairo-1.0-0 libcairo2 \
    libffi-dev shared-mime-info libgirepository1.0-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

COPY ./requirements.txt $APP_HOME/requirements.txt

RUN pip install --upgrade pip \
    && pip install -r requirements.txt --no-cache-dir

# create the app user
RUN addgroup --gid 1000 app && adduser --uid 1000 --gid 1000 --disabled-password --gecos "" app

# COPY . $APP_HOME

# change all directories owner to my user app
RUN chown -R app:app $APP_HOME && chown -R app:app $HOME

# Définir explicitement les permissions sur les répertoires média
RUN chmod -R 755 $APP_HOME/media

# change to the app user
USER app
