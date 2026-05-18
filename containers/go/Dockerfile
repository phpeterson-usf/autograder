FROM golang:1.25-bookworm

RUN apt-get update && apt-get install -y --no-install-recommends \
        make \
    && rm -rf /var/lib/apt/lists/*

# GOTOOLCHAIN=local prevents Go from trying to download a different
# toolchain version over the network (which --network=none would block
# anyway, producing a confusing error). If a student's go.mod requires
# a newer Go than this image ships, the build fails loudly instead.
#
# GOCACHE/GOPATH live under /tmp because the container runs as the host
# UID, which has no $HOME inside the image.
ENV GOTOOLCHAIN=local \
    GOCACHE=/tmp/gocache \
    GOPATH=/tmp/gopath \
    GOFLAGS=-buildvcs=false

WORKDIR /work
