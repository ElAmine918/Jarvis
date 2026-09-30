# ─── Stage 1: Builder ───────────────────────────────────────────────────────
# Stage temporaire : compile les dépendances Python.
# Ce stage est EXCLU de l'image finale.
FROM python:3.12-slim AS builder

WORKDIR /build
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ─── Stage 2: Runtime ───────────────────────────────────────────────────────
# Image finale minimale.
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    HOME=/app

WORKDIR /app

# Installer les binaires système nécessaires.
# gpg --dearmor ne fonctionne pas sans TTY pendant un build Docker :
# on utilise gpg --batch --no-tty pour éviter cette contrainte.
RUN apt-get update && apt-get install -y --no-install-recommends \
    procps \
    iproute2 \
    ca-certificates \
    gnupg \
    curl \
    && install -m 0755 -d /etc/apt/keyrings \
    && curl -fsSL https://download.docker.com/linux/debian/gpg \
       | gpg --batch --no-tty --dearmor -o /etc/apt/keyrings/docker.gpg \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/debian bookworm stable" \
       > /etc/apt/sources.list.d/docker.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends docker-ce-cli \
    # Retirer curl et gnupg : ils ne sont utiles que pour l'installation
    && apt-get remove -y --purge curl gnupg \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*

# Copier les dépendances Python depuis le stage builder
COPY --from=builder /install /usr/local

# Créer un utilisateur non-root dédié (UID/GID 1001)
# --no-create-home : pas de home directory sur le disque
# --shell /usr/sbin/nologin : aucun accès shell interactif
RUN groupadd --gid 1001 jarvis \
    && useradd --uid 1001 --gid 1001 --no-create-home --shell /usr/sbin/nologin jarvis

# Créer les dossiers applicatifs avec les bonnes permissions
RUN mkdir -p /app/data/skills /app/workspace /app/src \
    && chown -R jarvis:jarvis /app \
    && chmod 750 /app/workspace

# Copier le code source : appartient à root, lisible par jarvis, non modifiable
COPY --chown=root:jarvis src/ /app/src/
RUN chmod -R 550 /app/src

# Basculer vers l'utilisateur non-root
USER jarvis

EXPOSE 8080

# Healthcheck : si l'API ne répond plus, Docker peut redémarrer le conteneur
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python3 -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/v1/models')" || exit 1

CMD ["python3", "-m", "src.main"]
