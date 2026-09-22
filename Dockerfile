FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Guard against Windows line endings breaking the shell script.
RUN sed -i 's/\r$//' docker/entrypoint.sh && chmod +x docker/entrypoint.sh

WORKDIR /app/online_cinema
RUN DJANGO_DEBUG=0 DJANGO_SECRET_KEY=build-only python manage.py collectstatic --noinput

EXPOSE 8000
ENTRYPOINT ["/app/docker/entrypoint.sh"]