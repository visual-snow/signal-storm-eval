# Builds packetrusher:storm from source, since PacketRusher publishes no official
# image. A control-plane registration storm (multi-ue with the tunnel off) needs no
# CGO, no GSL, and no gtp5g kernel module, so a static CGO_ENABLED=0 build is enough.
# Pinned to a commit that includes the rapid-registration race fixes (Fix #187).
FROM golang:1.24 AS build
ARG PACKETRUSHER_REF=5bf8b4ed9350a4dfc732eb6a6074aa97d1426308
RUN git clone https://github.com/HewlettPackard/PacketRusher /src \
 && git -C /src checkout "$PACKETRUSHER_REF"
RUN cd /src && CGO_ENABLED=0 go build -o /packetrusher ./cmd/

FROM debian:bookworm-slim
# gettext-base provides envsubst, used at startup to render config.yml from the
# shared identity ConfigMap. timeout (coreutils) is already in the base image.
RUN apt-get update \
 && apt-get install -y --no-install-recommends gettext-base \
 && rm -rf /var/lib/apt/lists/*
COPY --from=build /packetrusher /usr/local/bin/packetrusher
ENTRYPOINT ["packetrusher"]
