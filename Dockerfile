# Use an official lightweight Python image
FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    # Hugging Face cache directory inside the container
    HF_HOME=/root/.cache/huggingface

# Set the working directory
WORKDIR /app

# Install system dependencies (e.g., curl for healthcheck) and clean up apt cache
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file first to leverage Docker layer caching
COPY requirements.txt .

# Install Python dependencies.
# MLOps Tip: We use `--extra-index-url` to install the CPU version of PyTorch by default.
# This dramatically reduces the Docker image size from ~5GB to ~1.5GB.
# If you plan to use GPU (CUDA), remove the `--extra-index-url` flag.
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt --extra-index-url https://download.pytorch.org/whl/cpu

# Copy the rest of the application code
COPY . .

# MLOps Tip: Pre-download the Hugging Face model during the image build phase.
# This prevents the container from re-downloading the model weights every time it starts up.
RUN python -c "from transformers import pipeline; pipeline('sentiment-analysis', model='nlptown/bert-base-multilingual-uncased-sentiment')"

# Expose the API port
EXPOSE 8000

# Add a healthcheck instruction to automatically monitor container status
HEALTHCHECK --interval=30s --timeout=30s --start-period=10s --retries=3 \
  CMD curl -f http://localhost:8000/ || exit 1

# Command to run the application using Uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
