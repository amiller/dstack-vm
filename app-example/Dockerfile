ARG PACKAGES="gcc neofetch"

# PKG_CACHE defaults to the "pkg-cache-local" stage in this image.
# Can be overridden to a custom image for reproducible builds.
ARG PKG_CACHE=pkg-cache-local

ARG BASE=python:alpine3.18@sha256:24680ddf8422899b24756d62b31eb5de782fbb42e9c2bb1c70f1f55fcf891721

FROM ${BASE} AS base

FROM base AS pkg-cache-local-base
ARG PACKAGES
RUN mkdir -p /etc/apk/cache && \
  apk update && \
  apk cache download --available --add-dependencies ${PACKAGES}

FROM scratch AS pkg-cache-local
COPY --from=pkg-cache-local-base /etc/apk/cache /etc/apk/cache

# pkg-cache is the stage to collect package cache files.
# This stage can be pushed for the sake of reproducible builds.
FROM ${PKG_CACHE} AS pkg-cache

FROM base
ARG PACKAGES
RUN \
  --mount=from=pkg-cache,source=/etc/apk/cache,target=/etc/apk/cache,rw \
  --network=none \
  apk add --no-network ${PACKAGES}
# The package signatures are verified by apk

ENV PIP_ROOT_USER_ACTION=ignore

RUN \
    : "Installing python dependencies" && \
    pip install --break-system-packages eth_account eth_abi flask requests 

WORKDIR /app/

COPY ./app.py ./
COPY ./templates/index.html ./templates/
COPY ./static/comp.png ./static/dstack.png ./static/

CMD ["python", "./app.py"]
