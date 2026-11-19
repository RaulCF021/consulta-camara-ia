FROM python:3.12-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && mkdir -p /data/operacao /data/fontes /data/frequencia && chown -R 1000:1000 /data
COPY . .
USER 1000:1000
CMD ["python","-m","uvicorn","servico:app","--host","0.0.0.0","--port","8000","--workers","1"]
