FROM debian:trixie-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
        make \
        openjdk-21-jre-headless \
    && rm -rf /var/lib/apt/lists/*

# The container runs as the host UID, which has no passwd entry inside the
# image; Java would otherwise fail trying to resolve user.home. Pointing
# HOME at a world-writable location avoids that.
ENV HOME=/tmp

WORKDIR /work
