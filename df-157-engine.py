
# K16: Concurrent-Spawn-Mutex (fcntl-based, Trinity-CONSERVATIVE 2026-05-17)
def k16_lock_or_exit(df_name: str):
    """Acquire exclusive lock or exit(3). Prevents concurrent DF runs."""
    import fcntl, os, sys
    lock_path = f"/tmp/df-trinity-{df_name}.lock"
    fd = os.open(lock_path, os.O_CREAT | os.O_WRONLY)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return fd
    except BlockingIOError:
        sys.exit(3)


# K13: External-Anchor-Mock-RFC3161 (Trinity-CONSERVATIVE 2026-05-17)
def k13_anchor(payload_hash: str) -> dict:
    """Mock RFC3161-style timestamp anchor."""
    from datetime import datetime, timezone
    return {
        "anchor_type": "rfc3161-mock",
        "iso_ts": datetime.now(timezone.utc).isoformat(),
        "payload_hash": payload_hash,
    }


# K12: HMAC-SHA256-Provenance (Trinity-CONSERVATIVE 2026-05-17)
def k12_provenance(payload: bytes, key: bytes = b"df-trinity-conservative-v1") -> dict:
    """Returns payload_hash + HMAC-SHA256 signature."""
    import hashlib, hmac
    return {
        "payload_hash": hashlib.sha256(payload).hexdigest(),
        "hmac_sha256": hmac.new(key, payload, hashlib.sha256).hexdigest(),
    }

"""DF-157 engine for PVG-Wargame-History-Aggregator.

Tracks Cross-LLM-Verdict-Trends in mock mode by default and writes a
JSON report without emitting recommendation or decision language.
"""

import re
import os
import json
import sys
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from datetime import datetime, timezone


DF_DIR = Path(__file__).parent
LOCK_DIR = Path("/tmp/df-157.lock")
DF_ID = "157"
DECISION_KEYWORDS_REGEX = re.compile(
    r"\b(entscheid[a-z]*|empfehl(?:e|en|t|st)|sollt(?:e|en|est)|recommend[a-z]*|decid[a-z]*|advis[a-z]*|propos[a-z]*)\b",
    re.IGNORECASE,
)


@dataclass
class TrackerOutput:
    welle: str = "25"
    df: str = "DF-157"
    iso_timestamp: str = ""
    source: str = "mock"
    wargames_total: int = 0
    adopt_count: int = 0
    modify_count: int = 0
    reject_count: int = 0
    verdict_per_llm: dict = field(default_factory=dict)


def iso_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _file_stable(path, min_age_sec=300) -> bool:
    p = Path(path)
    if not p.exists() or not p.is_file():
        return False
    try:
        stat = p.stat()
    except OSError:
        return False
    return (time.time() - stat.st_mtime) >= min_age_sec


def _remove_lock_dir_contents() -> None:
    if not LOCK_DIR.exists() or not LOCK_DIR.is_dir():
        return
    for child in LOCK_DIR.iterdir():
        try:
            if child.is_file() or child.is_symlink():
                child.unlink()
            elif child.is_dir():
                for nested in child.iterdir():
                    if nested.is_file() or nested.is_symlink():
                        nested.unlink()
                child.rmdir()
        except OSError:
            pass
    try:
        LOCK_DIR.rmdir()
    except OSError:
        pass


def acquire_lock_with_identity() -> bool:
    stale_after_sec = 6 * 60 * 60

    if LOCK_DIR.exists():
        try:
            age = time.time() - LOCK_DIR.stat().st_mtime
            if age >= stale_after_sec:
                _remove_lock_dir_contents()
        except OSError:
            return False

    try:
        LOCK_DIR.mkdir(mode=0o700)
    except FileExistsError:
        return False
    except OSError:
        return False

    identity = {
        "df": DF_ID,
        "pid": os.getpid(),
        "created_at": iso_now(),
        "cwd": str(Path.cwd()),
        "script": str(Path(__file__).resolve()),
    }
    try:
        (LOCK_DIR / "identity.json").write_text(
            json.dumps(identity, ensure_ascii=True, indent=2),
            encoding="utf-8",
        )
    except OSError:
        release_lock()
        return False

    return True


def release_lock() -> None:
    _remove_lock_dir_contents()


def k17_pre_action_verification(anchors) -> dict:
    missing = []
    for anchor in anchors:
        p = Path(anchor)
        if not p.exists():
            missing.append(str(p))

    return {
        "ok": not missing,
        "missing_anchors": missing,
        "env_tag": "real" if _is_real_api_enabled() else "mock",
    }


def _is_real_api_enabled() -> bool:
    raw = os.environ.get("DF_157_REAL_API_ENABLED", "false").strip().lower()
    return raw in {"1", "true", "yes", "y", "on"}


def scan_output_for_decision_keywords(text) -> list:
    if text is None:
        return []

    seen = set()
    hits = []
    for match in DECISION_KEYWORDS_REGEX.finditer(str(text)):
        token = match.group(0)
        key = token.lower()
        if key not in seen:
            seen.add(key)
            hits.append(token)
    return hits


def assert_no_decision_keywords(output) -> None:
    if isinstance(output, str):
        text = output
    else:
        text = json.dumps(output, ensure_ascii=True, sort_keys=True)

    hits = scan_output_for_decision_keywords(text)
    if hits:
        raise ValueError(
            "Q_0/K_0 keyword lock violation: " + ", ".join(sorted(hits, key=str.lower))
        )


def _load_mock_tracker_data() -> dict:
    mock_path = DF_DIR / "df-157-mock.json"
    if mock_path.exists() and _file_stable(mock_path, min_age_sec=0):
        try:
            raw = json.loads(mock_path.read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                return raw
        except (OSError, json.JSONDecodeError):
            pass

    return {
        "wargames_total": 0,
        "adopt_count": 0,
        "modify_count": 0,
        "reject_count": 0,
        "verdict_per_llm": {},
    }


def _coerce_int(value) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def collect_tracker_output() -> TrackerOutput:
    source = "real" if _is_real_api_enabled() else "mock"

    if source == "real":
        data = {
            "wargames_total": 0,
            "adopt_count": 0,
            "modify_count": 0,
            "reject_count": 0,
            "verdict_per_llm": {},
        }
    else:
        data = _load_mock_tracker_data()

    verdict_per_llm = data.get("verdict_per_llm", {})
    if not isinstance(verdict_per_llm, dict):
        verdict_per_llm = {}

    tracker = TrackerOutput(
        iso_timestamp=iso_now(),
        source=source,
        wargames_total=_coerce_int(data.get("wargames_total", 0)),
        adopt_count=_coerce_int(data.get("adopt_count", 0)),
        modify_count=_coerce_int(data.get("modify_count", 0)),
        reject_count=_coerce_int(data.get("reject_count", 0)),
        verdict_per_llm=verdict_per_llm,
    )

    assert_no_decision_keywords(asdict(tracker))
    return tracker


def _write_report(tracker: TrackerOutput, pav: dict) -> Path:
    report_dir = DF_DIR / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)

    date_part = datetime.now(timezone.utc).date().isoformat()
    report_path = report_dir / f"df-157-{date_part}.json"

    payload = {
        "pre_action_verification": pav,
        "tracker_output": asdict(tracker),
    }
    assert_no_decision_keywords(payload)

    report_path.write_text(
        json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return report_path


def main() -> int:
    if not acquire_lock_with_identity():
        return 3

    try:
        pav = k17_pre_action_verification([DF_DIR])
        assert_no_decision_keywords(pav)
        if not pav.get("ok"):
            return 3

        tracker = collect_tracker_output()
        _write_report(tracker, pav)
        return 0
    except Exception as exc:
        sys.stderr.write(str(exc) + "\n")
        return 3
    finally:
        release_lock()


if __name__ == "__main__":
    raise SystemExit(main())