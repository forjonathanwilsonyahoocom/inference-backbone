FROM python:3.13.17-slim-trixie

# Copy the uv executables from the official uv image.
# For reproducible builds, pin this tag to a specific version or image digest.
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

ENV UV_TOOL_DIR=/opt/uv-tools \
    UV_TOOL_BIN_DIR=/usr/local/bin \
    PATH="/usr/local/bin:${PATH}" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN uv tool install ast-outline \
    && ast-outline --version \
    && useradd --uid 10001 --create-home --shell /usr/sbin/nologin app

USER 10001:10001
WORKDIR /workspace

ENTRYPOINT ["ast-outline"]
