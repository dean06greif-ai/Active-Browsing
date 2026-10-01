import json
import random

from awaketoggle.config import Config, load
from awaketoggle.variants import VK_F13, VK_F24, make_plan, next_interval, random_keys, random_mouse, random_scroll
from tests.test_core import make


def rngs(n=300):
    return (random.Random(seed) for seed in range(n))


def test_random_mouse_returns_to_start():
    for rng in rngs():
        plan = random_mouse(rng)
        assert plan.kind == "mouse" and 6 <= len(plan.steps) <= 14
        assert sum(s[0] for s in plan.steps) == 0 and sum(s[1] for s in plan.steps) == 0
        x = y = peak = 0
        for dx, dy, pause in plan.steps:
            x, y = x + dx, y + dy
            peak = max(peak, abs(x), abs(y))
            assert 0 < pause < 0.05
        assert peak <= 28


def test_random_scroll_is_net_zero_and_small():
    for rng in rngs():
        plan = random_scroll(rng)
        deltas = [d for d, _ in plan.steps]
        assert sum(deltas) == 0
        assert all(abs(d) <= 60 for d in deltas)
        assert sum(p for _, p in plan.steps) < 2.0


def test_random_keys_only_f13_to_f24():
    for rng in rngs():
        plan = random_keys(rng)
        assert 1 <= len(plan.steps) <= 3
        assert all(VK_F13 <= vk <= VK_F24 for vk, _, _ in plan.steps)


def test_make_plan_respects_variants():
    cfg = Config(signal="random", random_variants=("scroll",))
    assert {make_plan(cfg, r).kind for r in rngs(50)} == {"scroll"}
    cfg = Config(signal="random")
    assert {make_plan(cfg, r).kind for r in rngs(200)} == {"mouse", "scroll", "keys"}
    assert make_plan(Config(), random.Random()).label == "Maus"
    assert make_plan(Config(signal="f15"), random.Random()).label == "F15"


def test_jitter_never_exceeds_interval():
    assert next_interval(Config(), random.Random(1)) == 60.0
    values = [next_interval(Config(jitter_percent=25), r) for r in rngs()]
    assert all(45.0 <= v <= 60.0 for v in values)
    assert len(set(values)) > 100


def test_engine_uses_jittered_target():
    api, _, eng = make(Config(jitter_percent=50), rng=random.Random(7))
    eng.set_active(True)
    api.advance(60_000)
    for _ in range(20):
        timeout = eng.step()
        assert 30.0 <= timeout <= 60.0
        api.advance(int(timeout * 1000))
    assert len(api.sent) >= 19


def test_engine_random_mode_varies_signals():
    api, _, eng = make(Config(signal="random"), rng=random.Random(3))
    eng.set_active(True)
    for _ in range(30):
        api.advance(60_000)
        eng.step()
    assert set(api.sent) == {"Mausbewegung", "Scrollen", "Tasten F13–F24"}
    assert "(" in eng.status.text


def test_config_new_keys(tmp_path):
    p = tmp_path / "config.json"
    p.write_text(json.dumps({"signal": "random", "random_variants": ["keys", "keys", "mouse"], "jitter_percent": 25}),
                 "utf-8")
    cfg, warnings = load(p)
    assert cfg.signal == "random" and cfg.random_variants == ("keys", "mouse") and cfg.jitter_percent == 25
    assert warnings == []
    p.write_text(json.dumps({"random_variants": [], "jitter_percent": 80}), "utf-8")
    cfg, warnings = load(p)
    assert cfg.random_variants == ("mouse", "scroll", "keys") and cfg.jitter_percent == 0 and len(warnings) == 2
