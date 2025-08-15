# Multi-stage build for smaller final image
FROM python:3.11-slim as python-base

# Install Python dependencies
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

FROM node:18-slim

# Install Python and copy Python dependencies from previous stage
RUN apt-get update && apt-get install -y \
    python3 \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy Python packages from python-base stage
COPY --from=python-base /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=python-base /usr/local/bin /usr/local/bin

# Set Python path
ENV PYTHONPATH=/usr/local/lib/python3.11/site-packages

# Create app directory
WORKDIR /app

# Copy package files
COPY package*.json ./

# Install Node.js dependencies
RUN npm ci --only=production

# Copy application code
COPY . .

# Create symlink for python3
RUN ln -sf /usr/bin/python3 /usr/bin/python3

# Set working directory for user files
WORKDIR /work

# Set entrypoint
ENTRYPOINT ["node", "/app/bin/rhythmic.js"]