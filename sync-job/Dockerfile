FROM python:3.11-slim

WORKDIR /app

# Create non-root user for security
RUN groupadd -r syncuser && useradd -r -g syncuser syncuser

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py .

USER syncuser

ENTRYPOINT ["python", "main.py"]
