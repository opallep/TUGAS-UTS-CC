FROM python:3.12-slim

WORKDIR /app
COPY app.py .

ENV DATA_DIR=/var/lib/backend_data \
    PORT=5000 \
    PYTHONUNBUFFERED=1

# Folder data ini nanti ditimpa oleh Docker Named Volume (link-hub-data)
RUN mkdir -p /var/lib/backend_data
VOLUME ["/var/lib/backend_data"]

EXPOSE 5000
CMD ["python", "app.py"]
