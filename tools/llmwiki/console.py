"""콘솔 인코딩 설정(표준 라이브러리만). init처럼 패키지 설치 전에도 쓰인다."""
import sys


def setup_console() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
        except Exception:
            pass
