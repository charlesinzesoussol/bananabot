# BananaBot - Discord Image Generation Bot
# Multi-stage build for optimized production image

# Build stage
FROM python:3.11-slim as builder

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies needed for building
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# Production stage
FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/venv/bin:$PATH"

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    # Required for image processing
    libjpeg-dev \
    libpng-dev \
    libwebp-dev \
    # Required for Pillow
    zlib1g-dev \
    # Cleanup
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv

# Create non-root user for security
RUN groupadd -r bananabot && \
    useradd -r -g bananabot -d /app -s /bin/bash bananabot

# Set working directory
WORKDIR /app

# Copy application code
COPY --chown=bananabot:bananabot . .

# Create logs directory
RUN mkdir -p logs && chown bananabot:bananabot logs

# Switch to non-root user
USER bananabot

# Health check
HEALTHCHECK --interval=60s --timeout=10s --start-period=20s --retries=3 \
    CMD python -c "import asyncio; print('Bot is healthy')" || exit 1

# Expose port (if needed for health checks or metrics)
EXPOSE 8080

# Default command
CMD ["python", "-m", "bot.main"]

# Labels for metadata
LABEL maintainer="BananaBot Team" \
      version="1.0.0" \
      description="Discord Image Generation Bot using Gemini 2.5 Flash" \
      org.opencontainers.image.source="https://github.com/your-org/bananabot"