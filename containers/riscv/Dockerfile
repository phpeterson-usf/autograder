FROM --platform=linux/riscv64 debian:trixie-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
        gcc \
        libc6-dev \
        make \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /work
