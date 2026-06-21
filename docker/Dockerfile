# spiceguard — zero-setup image with ngspice bundled.
#
# Build (from the repo root, so the build context includes src/):
#   docker build -t spiceguard -f docker/Dockerfile .
#
# Run (mount the directory containing your netlist as /work):
#   docker run --rm -v "$PWD:/work" spiceguard mycircuit.cir
#   docker run --rm -v "$PWD:/work" spiceguard kicad board.cir
#   cat board.cir | docker run --rm -i spiceguard kicad -
#
# Exit codes pass through: 0 TRUSTWORTHY, 1 FAILED, 2 SUSPECT, 3 ngspice-missing,
# 64 usage error.
FROM python:3.12-slim

# ngspice is spiceguard's only runtime dependency — bundle it.
RUN apt-get update \
    && apt-get install -y --no-install-recommends ngspice \
    && rm -rf /var/lib/apt/lists/*

# Install spiceguard from the repo source (exact code in this checkout).
WORKDIR /src
COPY pyproject.toml README.md LICENSE ./
COPY src ./src
RUN pip install --no-cache-dir .

# Run as a non-root user: spiceguard executes ngspice on netlists that may be
# untrusted (a SPICE deck can contain .control/shell directives), so drop privs.
RUN useradd -m -u 1000 sg
USER sg

# Users mount their netlists here; ngspice runs with this as the working dir so
# relative .include paths resolve.
WORKDIR /work

ENTRYPOINT ["spiceguard"]
CMD ["--help"]
