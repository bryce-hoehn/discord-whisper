FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libopus-dev \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install pywhispercpp

# Copy application code
COPY . .

# Run the bot
CMD ["python", "main.py"]