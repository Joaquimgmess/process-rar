FROM python:3.11-slim

RUN apt-get update && apt-get install -y wget && \
    wget https://www.rarlab.com/rar/rarlinux-x64-623.tar.gz && \
    tar -xzvf rarlinux-x64-623.tar.gz && \
    cp rar/unrar /usr/local/bin/unrar && \
    chmod +x /usr/local/bin/unrar && \
    rm -rf rarlinux-x64-623.tar.gz rar && \
    apt-get purge -y wget && apt-get autoremove -y && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . /app

RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 5000

CMD ["python", "app.py"] 