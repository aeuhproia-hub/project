FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Папка для JSON-хранилища. На Railway рекомендуется подключить Volume
# и примонтировать его сюда, чтобы данные не терялись при редеплое.
RUN mkdir -p /app/data

CMD ["python", "-m", "bot.main"]
