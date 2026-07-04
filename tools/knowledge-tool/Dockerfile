FROM docker.1ms.run/library/python:3.13-slim
RUN sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list.d/debian.sources 2>/dev/null || true
RUN echo "deb http://mirrors.aliyun.com/debian/ trixie main" > /etc/apt/apt-sources.list.d/alpine.list 2>/dev/null || true
RUN apt-get update && apt-get install -y --no-install-recommends gcc && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN mkdir -p /app/data/knowledge
EXPOSE 18081
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "18081"]
