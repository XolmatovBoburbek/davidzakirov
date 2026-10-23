FROM python:3.13-slim
WORKDIR /app
COPY app.py .
VOLUME /app/data
ENV PORT=8000
CMD ["python3", "app.py"]
