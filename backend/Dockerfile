FROM python:3.12-slim-bookworm

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    postgresql-client \
    texlive-base \
    texlive-luatex \
    texlive-lang-german \
    texlive-latex-extra \
    texlive-fonts-recommended \
    lmodern \
    locales \
    && sed -i '/de_DE.UTF-8/s/^# //' /etc/locale.gen \
    && locale-gen \
    && rm -rf /var/lib/apt/lists/*

ENV LANG=de_DE.UTF-8
ENV LC_ALL=de_DE.UTF-8

WORKDIR /backend

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend source (FastAPI app)
COPY backend/ /backend/

# Copy existing business-logic modules so the backend can import
# db_schema, db_helpers, student_loader, time_functions, export, etc.
COPY app/ /app/

ENV PYTHONPATH=/backend:/app

RUN useradd -m appuser \
    && mkdir -p /home/appuser/Zeugnisse \
    && chown -R appuser /backend /app /home/appuser/Zeugnisse
USER appuser

EXPOSE 8000

# --workers 1 is mandatory: db_schema.py uses a global ENGINE variable
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
