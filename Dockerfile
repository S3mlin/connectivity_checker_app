FROM python:slim

RUN apt-get update && apt-get install -y gcc libpq-dev

RUN python -m venv /venv
ENV PATH="/venv/bin:$PATH"

COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt

COPY . /app
WORKDIR /app

RUN mkdir -p /src/static
RUN SECRET_KEY=build_dummy python manage.py collectstatic --noinput

#RUN python manage.py collectstatic

ENV DJANGO_DEBUG_FALSE=1

ENV ALLOWED_HOSTS=127.0.0.1,localhost

CMD ["gunicorn", "--bind", "0.0.0.0:8888", "connectivity_checker_app.wsgi:application"]