# ---- base: Python + LuaLaTeX ----
FROM python:3.12-slim

ENV DEBIAN_FRONTEND=noninteractive

# TeXLive (LuaLaTeX), fonts, build tools for psycopg2, pg_dump for backups
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates locales curl \
    make gcc g++ libpq-dev \
    postgresql-client \
    texlive-base texlive-latex-recommended texlive-latex-extra \
    texlive-fonts-recommended texlive-luatex texlive-lang-german lmodern \
 && rm -rf /var/lib/apt/lists/*

# Locale for German umlauts
RUN sed -i 's/# de_DE.UTF-8 UTF-8/de_DE.UTF-8 UTF-8/' /etc/locale.gen && locale-gen
ENV LANG=de_DE.UTF-8 LC_ALL=de_DE.UTF-8

WORKDIR /app

# Install dependencies as root before switching user
COPY app/requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir -r requirements.txt

# Create unprivileged user and hand over ownership
RUN useradd -m appuser
COPY --chown=appuser:appuser app/ /app/

USER appuser

EXPOSE 8501
ENV STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

CMD ["streamlit", "run", "KompetenzenTool.py", \
     "--server.address=0.0.0.0", "--server.port=8501"]
