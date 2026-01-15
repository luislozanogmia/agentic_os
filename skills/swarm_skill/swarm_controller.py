#!/usr/bin/env python3
"""Swarm hierarchy assistant.

This helper prints the Cluster → Galaxy → Sun → Planet mapping for your multi-worker
swarm and generates templated worker briefs on demand.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import OrderedDict
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Tuple
from urllib import error as urlerror
from urllib import request

# Location for shared secrets.
ENV_PATH = Path("{{CLAUDE_HOME}}/.env")
GROQ_ENDPOINT = "https://api.groq.com/openai/v1/chat/completions"
USER_AGENT = "agent-swarm/0.1"

# Example worker slots grouped via Cluster → Galaxy → Sun → Planet.
WORKERS: Tuple[Dict[str, str], ...] = (
    {
        "worker": "W01",
        "cluster": "System",
        "galaxy": "Main Operations",
        "sun": "Orchestration",
        "planet": "Task Management",
        "lane": "system.ops.1",
    },
    {
        "worker": "W02",
        "cluster": "Research",
        "galaxy": "Information Gathering",
        "sun": "Web Search",
        "planet": "Topic Discovery",
        "lane": "research.search.1",
    },
)

SLOT_ORDER = ("agent", "location", "subject", "action", "outcome", "timing")


def _load_env() -> Dict[str, str]:
    """Parse .env into a dictionary."""
    result: Dict[str, str] = {}
    if not ENV_PATH.exists():
        return result
    for raw in ENV_PATH.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        result[key.strip()] = value.strip().strip('"').strip("'")
    return result


def _require_env(name: str) -> str:
    """Fetch an environment variable, falling back to ~/.claude/.env."""
    value = os.environ.get(name)
    if value:
        return value
    env_values = _load_env()
    value = env_values.get(name)
    if value:
        os.environ[name] = value
        return value
    
    print(f"\n⚠️  MISSING CONFIGURATION: {name} is required.")
    print(f"👉 Please set it in your environment or {ENV_PATH}\n")
    sys.exit(1)


def _group_by(keys: Iterable[str]) -> OrderedDict[str, List[Dict[str, str]]]:
    """Return OrderedDict grouping workers by the specified keys."""
    grouping: OrderedDict[str, List[Dict[str, str]]] = OrderedDict()
    for worker in WORKERS:
        group_key = " / ".join(worker[key] for key in keys)
        grouping.setdefault(group_key, []).append(worker)
    return grouping


def cmd_lanes(_: argparse.Namespace) -> None:
    """Print all worker slots as JSON objects."""
    for worker in WORKERS:
        print(json.dumps(worker))


def cmd_blueprint(_: argparse.Namespace) -> None:
    """Display the hierarchy in Cluster → Galaxy → Sun → Planet order."""
    clusters = OrderedDict()
    for worker in WORKERS:
        cluster = clusters.setdefault(worker["cluster"], OrderedDict())
        galaxy = cluster.setdefault(worker["galaxy"], OrderedDict())
        sun = galaxy.setdefault(worker["sun"], [])
        sun.append({"planet": worker["planet"], "worker": worker["worker"], "lane": worker["lane"]})

    for cluster_name, galaxies in clusters.items():
        print(f"# Cluster: {cluster_name}")
        for galaxy_name, suns in galaxies.items():
            print(f"  - Galaxy: {galaxy_name}")
            for sun_name, planets in suns.items():
                print(f"    • Sun: {sun_name}")
                for planet in planets:
                    print(
                        f"        · Planet: {planet['planet']} "
                        f"(worker {planet['worker']} | lane {planet['lane']})"
                    )
        print("")


def cmd_template(args: argparse.Namespace) -> None:
    """Emit a worker brief template."""
    payload = OrderedDict()
    payload["template_id"] = f"seed-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
    payload["worker"] = args.worker
    payload["cluster"] = args.cluster
    payload["galaxy"] = args.galaxy
    payload["sun"] = args.sun
    payload["planet"] = args.planet
    for slot_name in SLOT_ORDER:
        value = getattr(args, slot_name)
        if not value:
            raise SystemExit(f"Missing slot value for {slot_name}")
        payload[slot_name] = value
    if args.notes:
        payload["notes"] = args.notes
    print(json.dumps(payload, indent=2))


def cmd_matrix(_: argparse.Namespace) -> None:
    """Render a quick tabular view by cluster."""
    grouping = _group_by(("cluster",))
    for group, rows in grouping.items():
        print(f"{group}")
        for worker in rows:
            print(
                f"  - {worker['worker']} :: {worker['galaxy']} → {worker['sun']} → "
                f"{worker['planet']} [{worker['lane']}]"
            )
        print("")


def _call_groq(model: str, system_prompt: str, user_prompt: str, temperature: float, max_tokens: int) -> Dict[str, object]:
    """Send a chat completion request to Groq."""
    api_key = _require_env("GROQ_API_KEY")
    body = json.dumps(
        {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
    ).encode("utf-8")
    req = request.Request(
        GROQ_ENDPOINT,
        data=body,
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": USER_AGENT,
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=60) as response:
            payload = response.read().decode("utf-8")
            return json.loads(payload)
    except urlerror.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore")
        raise SystemExit(f"Groq API error ({exc.code}): {detail}") from exc
    except urlerror.URLError as exc:
        raise SystemExit(f"Groq API network error: {exc.reason}") from exc


def cmd_groq(args: argparse.Namespace) -> None:
    """Call Groq with a worker brief prompt."""
    result = _call_groq(
        model=args.model,
        system_prompt=args.system,
        user_prompt=args.prompt,
        temperature=args.temperature,
        max_tokens=args.max_tokens,
    )
    if args.raw:
        print(json.dumps(result, indent=2))
        return
    try:
        content = result["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError, AttributeError):
        print(json.dumps(result, indent=2))
        return
    print(content)

def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Reference helper for worker swarm hierarchy.")
    sub = parser.add_subparsers(dest="command", required=True)

    lanes_p = sub.add_parser("lanes", help="Print each worker slot as JSON row.")
    lanes_p.set_defaults(func=cmd_lanes)

    blueprint_p = sub.add_parser("blueprint", help="Pretty-print the Cluster → Galaxy → Sun → Planet tree.")
    blueprint_p.set_defaults(func=cmd_blueprint)

    matrix_p = sub.add_parser("matrix", help="Summarize workers grouped by cluster.")
    matrix_p.set_defaults(func=cmd_matrix)

    template_p = sub.add_parser("template", help="Generate a worker brief.")
    template_p.add_argument("--worker", required=True)
    template_p.add_argument("--cluster", required=True)
    template_p.add_argument("--galaxy", required=True)
    template_p.add_argument("--sun", required=True)
    template_p.add_argument("--planet", required=True)
    template_p.add_argument("--agent", required=True)
    template_p.add_argument("--location", required=True)
    template_p.add_argument("--subject", required=True)
    template_p.add_argument("--action", required=True)
    template_p.add_argument("--outcome", required=True)
    template_p.add_argument("--timing", required=True)
    template_p.add_argument("--notes")
    template_p.set_defaults(func=cmd_template)

    groq_p = sub.add_parser("groq", help="Send a structured prompt to Groq.")
    groq_p.add_argument("--prompt", required=True)
    groq_p.add_argument("--system", default="You are a swarm worker executing structured assignments.")
    groq_p.add_argument("--model", default="llama-3.1-70b-versatile")
    groq_p.add_argument("--temperature", type=float, default=0.2)
    groq_p.add_argument("--max-tokens", type=int, default=512, dest="max_tokens")
    groq_p.add_argument("--raw", action="store_true")
    groq_p.set_defaults(func=cmd_groq)

    args = parser.parse_args(argv)
    args.func(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
