FROM docker.1ms.run/library/python:3.13-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8883

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8883"]
