#!/usr/bin/env python3
"""Regenerate README images (graphs + CLI screenshot)."""

from __future__ import annotations

import io
import random
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
IMAGES = REPO / "images"
FIXTURE = IMAGES / "fixtures" / "demo-vault"


def render_graph(path: Path, edge_probability: float, seed: int) -> None:
    import matplotlib.pyplot as plt
    import networkx as nx

    random.seed(seed)
    node_count = 280
    graph = nx.Graph()
    graph.add_nodes_from(range(node_count))

    hub = random.randint(0, node_count - 1)
    spokes = random.sample(range(node_count), k=42)
    for node in spokes:
        graph.add_edge(hub, node)
        for _ in range(3):
            if random.random() < edge_probability:
                other = random.randint(0, node_count - 1)
                if other != node:
                    graph.add_edge(node, other)

    positions = nx.spring_layout(graph, seed=seed, k=0.45, iterations=80)
    degrees = dict(graph.degree())
    sizes = [18 + degrees[node] * 9 for node in graph.nodes()]

    fig, axis = plt.subplots(figsize=(8, 6), facecolor="white")
    axis.set_facecolor("white")
    nx.draw_networkx_edges(
        graph,
        positions,
        ax=axis,
        width=0.35,
        alpha=0.25,
        edge_color="#9aa0a6",
    )
    nx.draw_networkx_nodes(
        graph,
        positions,
        ax=axis,
        node_size=sizes,
        node_color="#4a4a4a",
        linewidths=0,
    )
    axis.axis("off")
    fig.tight_layout(pad=0)
    fig.savefig(path, dpi=160, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def capture_cli_output() -> str:
    cmd = [
        sys.executable,
        "-m",
        "vault_linker.cli",
        str(FIXTURE),
        "--dry-run",
        "-v",
        "--jobs",
        "8",
        "--no-self-links",
    ]
    completed = subprocess.run(
        cmd,
        cwd=REPO,
        capture_output=True,
        text=True,
        check=True,
    )
    lines = completed.stdout.strip().splitlines()
    header = [
        f"vault-linker % vaultlinker {FIXTURE.name}/ --dry-run -v --jobs 8",
        "",
    ]
    # Keep terminal height readable in README.
    tail = lines[-18:] if len(lines) > 18 else lines
    return "\n".join(header + tail)


def render_terminal(path: Path, text: str) -> None:
    from PIL import Image, ImageDraw, ImageFont

    font_size = 15
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Menlo.ttc", font_size)
    except OSError:
        font = ImageFont.load_default()

    lines = text.splitlines()
    line_height = font_size + 4
    padding = 24
    width = 920
    height = padding * 2 + line_height * len(lines)

    image = Image.new("RGB", (width, height), "#1e1e1e")
    draw = ImageDraw.Draw(image)
    y = padding
    for line in lines:
        color = "#7ee787" if line.startswith("vault-linker") else "#d4d4d4"
        if "%" in line and "vaultlinker" in line:
            color = "#7ee787"
        if "Total links" in line or "Total files" in line:
            color = "#e5c07b"
        if "dry run" in line:
            color = "#9cdcfe"
        draw.text((padding, y), line, fill=color, font=font)
        y += line_height

    image.save(path, format="PNG")


def main() -> None:
    IMAGES.mkdir(parents=True, exist_ok=True)
    render_graph(IMAGES / "before.png", edge_probability=0.08, seed=11)
    render_graph(IMAGES / "after.png", edge_probability=0.55, seed=23)
    cli_text = capture_cli_output()
    render_terminal(IMAGES / "usage.png", cli_text)
    print(f"Wrote images to {IMAGES}")


if __name__ == "__main__":
    main()
