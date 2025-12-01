FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 libglib2.0-0 \
 && rm -rf /var/lib/apt/lists/*

COPY requirements-docker.txt ./

RUN python -m pip install --no-cache-dir --upgrade pip \
 && python -m pip install --no-cache-dir -r requirements-docker.txt

COPY logger.py .
COPY tests/dummy_data/automated_reporting ./tests/dummy_data/automated_reporting
COPY onboard_system ./onboard_system

ENV PYTHONPATH=/app

CMD ["python", "onboard_system/automated_reporting/generate_daily_report.py", "--use_dummy_data"]