# 1) Base image with python3.11
FROM python:3.11-slim

ENV TZ=Australia/Sydney \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# 2) System dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        tzdata \
        ffmpeg \
        build-essential \
    && ln -snf /usr/share/zoneinfo/$TZ /etc/localtime \
    && echo $TZ > /etc/timezone \
    && dpkg-reconfigure --frontend noninteractive tzdata \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 3) Pre-copy requirements
COPY requirements.txt .

# 4) Install torch 
RUN pip install --no-cache-dir \
        --index-url https://download.pytorch.org/whl/cpu \
        "torch==2.1.2" "torchaudio==2.1.2" \
    && pip install --no-cache-dir -r requirements.txt \
    && python -m nltk.downloader averaged_perceptron_tagger_eng -d /usr/local/nltk_data
# 5) Copy project (excluding models via .dockerignore)
COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]