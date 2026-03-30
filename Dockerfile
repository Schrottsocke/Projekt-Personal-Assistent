FROM python:3.11-slim

WORKDIR /app

# System-Dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    tesseract-ocr \
    libmagic1 \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# Python Dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# App-Code
COPY . .

# Daten- und Log-Verzeichnisse
RUN mkdir -p data logs

# Kein Root
RUN useradd -m -u 1000 assistant && chown -R assistant:assistant /app
USER assistant

CMD ["python", "main.py"]
