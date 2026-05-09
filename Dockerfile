FROM ghcr.io/astral-sh/uv:python3.13-bookworm
RUN adduser agent
USER agent
WORKDIR /home/agent
COPY pyproject.toml README.md ./
COPY src src
RUN uv sync

# Change this line:
CMD ["uv", "run", "python", "src/server.py", "--host", "0.0.0.0", "--port", "9009"]