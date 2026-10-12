# Spotafriend on a Hugging Face Docker Space: one always-on container with a
# permanent https://<owner>-<space>.hf.space address.
#
# The Space only needs this file and README.md. The code comes from GitHub and
# the song dataset from its official Hugging Face mirror (BSD license), both at
# build time. To pick up new commits from GitHub, use "Factory rebuild" in the
# Space's settings.
FROM python:3.11-slim

RUN apt-get update \
 && apt-get install -y --no-install-recommends git curl \
 && rm -rf /var/lib/apt/lists/*

ARG REPO=https://github.com/yukezhaoyz/spotafriend.git
ARG REF=main
RUN git clone --depth 1 --branch "$REF" "$REPO" /app \
 && curl -fsSL -o /app/dataset.csv \
      https://huggingface.co/datasets/maharshipandya/spotify-tracks-dataset/resolve/main/dataset.csv \
 && pip install --no-cache-dir -r /app/backend/requirements.txt gunicorn==23.0.0

# Spaces run containers as user 1000. The app only reads files; its database
# lives in memory.
RUN useradd -m -u 1000 user
USER user
WORKDIR /app/backend

ENV PYTHONUNBUFFERED=1 \
    SPOTAFRIEND_DEBUG=off \
    SPOTAFRIEND_ALLOWED_HOSTS=.hf.space

EXPOSE 7860
# One process on purpose: everything lives in that process's in-memory
# database. Threads handle requests side by side; the app's middleware queues
# writes (see tracks/middleware.py).
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:7860", "--workers", "1", "--threads", "8", "--timeout", "120"]
