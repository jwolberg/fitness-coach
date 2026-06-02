# Backend API image (P0-T2). Slim Python base; installs deps, copies app, runs uvicorn.
FROM python:3.11-slim

WORKDIR /app

# Install dependencies first so the layer caches when only app code changes.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY data ./data

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
