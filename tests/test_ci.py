"""CI assertion wrapper: keyless demo + server endpoint checks.

Test 1 runs the advertised keyless demo (`python seed_and_run.py`).
Test 2 mirrors main.py's startup exactly (init_db, then uvicorn without
reload) against a test-scoped DATABASE_URL, health-polls with a bounded
RETRIES x INTERVAL budget, loads the sample dataset, and asserts the
deterministic metrics. Server lifecycle: log captured to file and dumped
on failure, PID owned by the test, teardown in finally, process death
asserted. Child output is pinned to UTF-8 (PYTHONIOENCODING) so frozen
lines containing the euro sign are byte-identical on every OS.
Assertions cover counts, totals, and exit codes only — never timestamps.
"""
import json
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PORT = 8765
BASE = f"http://127.0.0.1:{PORT}"
REQ_TIMEOUT_S = 30
TIMEOUT_S = 300
# Budget >= 3x measured cold-start (1.15s, fresh venv, 2026-07-27
# rehearsal): 30 retries x 1.0s, explicit and bounded.
HEALTH_RETRIES = 30
HEALTH_INTERVAL_S = 1.0

# Frozen 2026-07-27 from piped fresh-clone runs, Python 3.12.0 and
# 3.14.4: two identical fresh-state runs + one PYTHONHASHSEED-varied
# run per interpreter, identical after stripping logger wall-clock
# prefixes only. All values derive from the frozen 75-record
# data/sample_outcomes.json through fixed multipliers; nothing in the
# metric path reads the clock (stored timestamps are never compared).
FROZEN_DEMO = [
    "Loaded 75 leads | 0 rejected",
    "Total in DB: 75",
    "  Total leads:              75",
    "  Net impact:               €119,240.00",
    "  Conversion rate:          41.3%",
    "[ ANALYSIS ] (simulated)",
    "Simulation complete. No OpenAI credits used.",
]
EXPECT_TOTAL_LEADS = 75
EXPECT_NET_IMPACT = 119240.0


def _keyless_env(tmp_path, dbname):
    env = dict(os.environ, USE_SIMULATION_FALLBACK="true",
               DATABASE_URL=str(tmp_path / dbname),
               PYTHONIOENCODING="utf-8")
    env.pop("OPENAI_API_KEY", None)
    return env


def _get(path, timeout=REQ_TIMEOUT_S):
    with urllib.request.urlopen(BASE + path, timeout=timeout) as resp:
        return resp.status, json.loads(resp.read())


def _post_json(path, payload):
    req = urllib.request.Request(
        BASE + path, data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=REQ_TIMEOUT_S) as resp:
        return resp.status, json.loads(resp.read())


def test_keyless_demo_cli(tmp_path):
    env = _keyless_env(tmp_path, "ci_demo.db")
    r = subprocess.run(
        [sys.executable, "seed_and_run.py"],
        cwd=ROOT, env=env, capture_output=True, text=True,
        encoding="utf-8", timeout=TIMEOUT_S,
    )
    assert r.returncode == 0, f"exit {r.returncode}\n{r.stdout}\n{r.stderr}"
    for frozen in FROZEN_DEMO:
        assert frozen in r.stdout, f"missing frozen line: {frozen!r}"


def test_server_endpoints_keyless(tmp_path):
    env = _keyless_env(tmp_path, "ci_server.db")
    # main.py's startup sequence is init_db() then uvicorn.run; mirror
    # step 1 against the same test-scoped DB, then run uvicorn without
    # the demo launcher's reload watcher.
    init = subprocess.run(
        [sys.executable, "-c", "from database.db import init_db; init_db()"],
        cwd=ROOT, env=env, capture_output=True, text=True, timeout=60,
    )
    assert init.returncode == 0, init.stdout + init.stderr

    log_path = tmp_path / "server.log"
    with open(log_path, "w") as log:
        proc = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "api:app", "--port", str(PORT)],
            cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT,
        )
        try:
            healthy = False
            for _ in range(HEALTH_RETRIES):
                if proc.poll() is not None:
                    break
                try:
                    status, _body = _get("/health", timeout=5)
                    if status == 200:
                        healthy = True
                        break
                except OSError:
                    time.sleep(HEALTH_INTERVAL_S)
            assert healthy and proc.poll() is None, (
                f"server not healthy within {HEALTH_RETRIES}x{HEALTH_INTERVAL_S}s; "
                f"exit={proc.poll()}\n--- server.log ---\n{log_path.read_text()}"
            )

            records = json.loads(
                (ROOT / "data" / "sample_outcomes.json").read_text()
            )
            status, body = _post_json("/load", records)
            assert status == 200
            assert body["loaded"] == EXPECT_TOTAL_LEADS
            assert body["rejected"] == 0
            assert body["total_in_db"] == EXPECT_TOTAL_LEADS

            status, body = _get("/impact/summary")
            assert status == 200
            assert body["metrics"]["total_leads"] == EXPECT_TOTAL_LEADS
            assert body["metrics"]["net_impact"] == EXPECT_NET_IMPACT

            status, body = _get("/impact")
            assert status == 200
            assert body["analysis"]["simulated"] is True
        finally:
            if proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(10)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait(10)
            assert proc.poll() is not None, "server process still alive after teardown"
