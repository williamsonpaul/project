FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

WORKDIR /app

COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/
COPY config/ ./config/

RUN groupadd --system appgroup && \
    useradd --system --gid appgroup appuser

USER appuser

ENTRYPOINT ["python", "src/main.py"]
CMD ["--help"]
