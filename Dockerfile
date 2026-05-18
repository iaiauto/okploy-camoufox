FROM python:3.12-slim

# Firefox runtime dependencies required by Camoufox
RUN apt-get update && apt-get install -y \
    libgtk-3-0 \
    libasound2 \
    libx11-xcb1 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libpango-1.0-0 \
    libcairo2 \
    libatspi2.0-0 \
    libdbus-glib-1-2 \
    libxt6 \
    xvfb \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps first (layer cache)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Download Camoufox browser at build time (~300MB) — not at runtime
RUN camoufox fetch

COPY app.py .

EXPOSE 8000

# Xvfb required for headless Firefox on Linux
CMD Xvfb :99 -screen 0 1280x800x24 -nolisten tcp & \
    DISPLAY=:99 uvicorn app:app --host 0.0.0.0 --port 8000 --workers 1
