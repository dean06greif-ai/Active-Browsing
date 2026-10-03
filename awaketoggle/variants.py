"""Signalpläne: feste Signale und zufällige, aber harmlose Varianten (netto ohne Wirkung)."""
import random
from dataclasses import dataclass


VK_F13, VK_F15, VK_F24 = 0x7C, 0x7E, 0x87
VARIANT_LABELS = {"mouse": "Mausbewegung", "scroll": "Scrollen", "keys": "Tasten F13–F24"}


@dataclass(frozen=True)
class Plan:
    kind: str  # mouse: (dx, dy, pause_s) | scroll: (delta, pause_s) | keys: (vk, hold_s, pause_s)
    steps: tuple
    label: str


def fixed_mouse() -> Plan:
    return Plan("mouse", ((1, 0, 0.0), (-1, 0, 0.0)), "Maus")


def fixed_f15() -> Plan:
    return Plan("keys", ((VK_F15, 0.0, 0.0),), "F15")


def random_mouse(rng: random.Random) -> Plan:
    out = []
    for _ in range(rng.randint(3, 7)):
        dx, dy = rng.randint(-4, 4), rng.randint(-4, 4)
        out.append((dx or 1, dy, rng.uniform(0.008, 0.04)))
    back = [(-dx, -dy, rng.uniform(0.008, 0.04)) for dx, dy, _ in reversed(out)]
    return Plan("mouse", tuple(out + back), VARIANT_LABELS["mouse"])


def random_scroll(rng: random.Random) -> Plan:
    delta = rng.choice((-1, 1)) * rng.randint(15, 60)
    n = rng.randint(1, 3)
    there = [(delta, rng.uniform(0.04, 0.15)) for _ in range(n)]
    pause = [(0, rng.uniform(0.2, 0.8))]
    back = [(-delta, rng.uniform(0.04, 0.15)) for _ in range(n)]
    return Plan("scroll", tuple(there + pause + back), VARIANT_LABELS["scroll"])


def random_keys(rng: random.Random) -> Plan:
    steps = tuple((rng.randint(VK_F13, VK_F24), rng.uniform(0.03, 0.12), rng.uniform(0.08, 0.4))
                  for _ in range(rng.randint(1, 3)))
    return Plan("keys", steps, VARIANT_LABELS["keys"])


_RANDOM = {"mouse": random_mouse, "scroll": random_scroll, "keys": random_keys}


def make_plan(cfg, rng: random.Random) -> Plan:
    if cfg.signal == "f15":
        return fixed_f15()
    if cfg.signal == "random":
        return _RANDOM[rng.choice(cfg.random_variants)](rng)
    return fixed_mouse()


def next_interval(cfg, rng: random.Random) -> float:
    """Zufälliger Abstand, nie länger als der eingestellte (damit die Leerlaufgrenze sicher bleibt)."""
    base = float(cfg.interval_seconds)
    if not cfg.jitter_percent:
        return base
    return max(rng.uniform(base * (1 - cfg.jitter_percent / 100), base), 5.0)
