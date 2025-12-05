#FROM python:3.11-slim
#
## System deps
#RUN apt-get update && apt-get install -y --no-install-recommends \
#    ca-certificates \
# && rm -rf /var/lib/apt/lists/*
#
#WORKDIR /app
#
## Copy code + model + deps
#COPY app.py xgb_model.pkl requirements.txt /app/
#
#RUN pip install --no-cache-dir -r requirements.txt
#
## Default envs (overridable in Kubernetes)
#ENV MODEL_PATH=/app/xgb_model.pkl \
#    FLASK_ENV=production
#
#EXPOSE 5000
#
#CMD ["python", "app.py"]


FROM python:3.10-slim

# Avoid Python buffering issues
ENV PYTHONUNBUFFERED=1

# Create app dir
WORKDIR /app

# Install system dependencies (optional, but often useful)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
  && rm -rf /var/lib/apt/lists/*

# Copy dependency list and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy code + model artifacts
COPY app_yassmine.py /app/app_yassmine.py
COPY rf_model.pkl /app/rf_model.pkl
COPY robust_scaler.pkl /app/robust_scaler.pkl

# Default env variables (can be overridden in Kubernetes)
ENV MODEL_PATH=/app/rf_model.pkl
ENV SCALER_PATH=/app/robust_scaler.pkl

# Flask listens on 5000
EXPOSE 5000

# Start the app (scheduler + Flask API)
CMD ["python", "app_yassmine.py"]

