FROM python:3.13-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/

# Create a dedicated non-root user and switch to it before running the app.
# Running as root inside a container is unnecessary privilege — if the app
# were ever compromised, a non-root process limits what an attacker could
# do inside the container (can't install packages, modify system files, etc.)
RUN useradd --create-home --shell /bin/bash appuser
USER appuser

EXPOSE 8000
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
