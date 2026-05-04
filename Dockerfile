# ---- base: Python + LuaLaTeX ----
FROM python:3.12-slim-bookworm

ENV DEBIAN_FRONTEND=noninteractive

# Force HTTPS for apt (HTTP port 80 unreliable in WSL2/Docker),
# force IPv4 to avoid WSL2 IPv6 routing issues, add retries.
RUN sed -i 's|URIs: http://|URIs: https://|g' /etc/apt/sources.list.d/debian.sources \
 && printf 'Acquire::Retries "5";\nAcquire::https::Timeout "120";\nAcquire::ForceIPv4 "true";\n' \
    > /etc/apt/apt.conf.d/80network \
 && apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates locales \
    postgresql-client \
    texlive-base texlive-latex-recommended texlive-latex-extra \
    texlive-fonts-recommended texlive-luatex texlive-lang-german lmodern \
 && rm -rf /var/lib/apt/lists/*

# Locale for German umlauts
RUN sed -i 's/# de_DE.UTF-8 UTF-8/de_DE.UTF-8 UTF-8/' /etc/locale.gen && locale-gen
ENV LANG=de_DE.UTF-8 LC_ALL=de_DE.UTF-8

WORKDIR /app

# Create venv and install dependencies into it
ENV VIRTUAL_ENV=/app/.venv
RUN python -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

COPY app/requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir -r requirements.txt

# Create unprivileged user and hand over ownership
RUN useradd -m appuser
COPY --chown=appuser:appuser app/ /app/
RUN chown -R appuser:appuser $VIRTUAL_ENV

USER appuser

EXPOSE 8501
ENV STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

CMD ["streamlit", "run", "KompetenzenTool.py", \
     "--server.address=0.0.0.0", "--server.port=8501"]
