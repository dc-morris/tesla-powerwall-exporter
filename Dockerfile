FROM python:3.12-alpine
WORKDIR /app
COPY exporter.py .
EXPOSE 9998
CMD ["python3", "exporter.py"]
