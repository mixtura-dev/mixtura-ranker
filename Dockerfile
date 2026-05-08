FROM python:3.13-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY . .

RUN pip install --upgrade pip
RUN pip install uv
RUN uv pip install --system --editable .

ENV PYTHONUNBUFFERED=1

CMD ["sh", "entrypoint.sh"]