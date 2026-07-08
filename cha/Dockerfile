FROM python:3.12-slim

# LibreOffice (headless) is used to convert generated .docx Approval Notes to PDF.
# This adds ~400MB to the image; remove if PDF export via LibreOffice is not required
# (the app still works and falls back to serving the .docx file instead).
RUN apt-get update && apt-get install -y --no-install-recommends \
    libreoffice --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p uploads exports

ENV FLASK_ENV=production
EXPOSE 5000

CMD ["gunicorn", "-c", "gunicorn.conf.py", "app:app"]
