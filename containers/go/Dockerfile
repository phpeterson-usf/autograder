FROM debian:trixie-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates \
        golang-go \
        make \
    && rm -rf /var/lib/apt/lists/*

# Go's build cache needs a writable location that does not depend on $HOME,
# since the container runs as the host user (UID may not have a passwd entry).
ENV GOCACHE=/tmp/gocache GOPATH=/tmp/gopath GOFLAGS=-buildvcs=false

WORKDIR /work
