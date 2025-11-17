# Use a Conda-compatible base image
FROM continuumio/miniconda3

# Set the working directory in the container
WORKDIR /app

# Copy application code
COPY . .

# Copy Conda environment file
COPY environment.yml .

# Create and activate the Conda environment with improved error logging
RUN conda env create -f environment.yml --debug > conda_log.txt 2>&1 || (cat conda_log.txt && false)

# Set PATH to include the Conda environment's executables
ENV PATH /opt/conda/envs/propalyst-env/bin:$PATH

# Install system dependencies for Playwright (required for Crawl4AI)
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    ca-certificates \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install Playwright and its dependencies using the conda environment
RUN /bin/bash -c "source activate propalyst-env && playwright install --with-deps chromium"

# Create data directory if it doesn't exist
RUN mkdir -p /app/data

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PORT=8000

# Expose the port your FastAPI app runs on
EXPOSE 8000

# Command to run the app with uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
