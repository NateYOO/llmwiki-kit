"""`llmwiki serve` — site/를 127.0.0.1에서 띄운다 (표준 라이브러리 http.server).
- 백그라운드로 떼어 내 실행하고 바로 돌아온다(Codex 명령이 끝나도 화면이 살아 있게).
  Windows: pythonw + DETACHED_PROCESS|CREATE_NEW_PROCESS_GROUP(가능하면 CREATE_BREAKAWAY_FROM_JOB), macOS/Linux: start_new_session.
- 상태 파일 `.llmwiki/serve.json`(pid·port·token·root) + /__llmwiki__/health 로 '우리 서버'인지 확인 → 이미 켜져 있으면 재사용.
- 포트가 다른 프로그램에 쓰이고 있으면 다음 포트(최대 20개).
- 끄기: `llmwiki serve --stop` (토큰이 맞는 POST /__llmwiki__/stop, 안 되면 pid 종료).
워커 실행: python -m llmwiki.serve --worker --root <작업 폴더> --port <시작 포트>"""
from __future__ import annotations

import json
import os
import secrets
import subprocess
import sys
import time
import urllib.request
from pathlib import Path
from typing import Any

DEFAULT_PORT = 8765
TRIES = 20
HEALTH = "/__llmwiki__/health"
STOP = "/__llmwiki__/stop"


def state_path(root: Path) -> Path:
    return root / ".llmwiki" / "serve.json"


def read_state(root: Path) -> dict[str, Any] | None:
    try:
        return json.loads(state_path(root).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def health(port: int, timeout: float = 1.0) -> dict[str, Any] | None:
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}{HEALTH}", timeout=timeout) as r:  # noqa: S310 — localhost
            return json.loads(r.read().decode("utf-8"))
    except Exception:  # noqa: BLE001
        return None


def _same_root(h: dict | None, root: Path) -> bool:
    if not h or h.get("app") != "llmwiki":
        return False
    try:
        return Path(h.get("root", "")).resolve() == root.resolve()
    except OSError:
        return False


def running(root: Path) -> dict[str, Any] | None:
    """이 폴더의 화면 서버가 살아 있으면 {'port', 'pid', 'url'}."""
    st = read_state(root) or {}
    ports = [st["port"]] if st.get("port") else []
    ports += [p for p in range(DEFAULT_PORT, DEFAULT_PORT + 3) if p not in ports]  # 상태 파일이 지워진 경우 대비
    for port in ports:
        h = health(port)
        if _same_root(h, root):
            return {"port": port, "pid": h.get("pid"), "url": f"http://127.0.0.1:{port}/"}
    return None


# ------------------------------------------------------------------ 워커(실제 서버)
def _worker(root: Path, start_port: int) -> int:
    import functools
    import http.server
    import socketserver
    import threading

    site = root / "site"
    token = secrets.token_hex(16)

    class Handler(http.server.SimpleHTTPRequestHandler):
        """라우팅 표: (메서드, 경로) → 처리 함수. 나머지 GET은 site/ 정적 파일."""

        def log_message(self, *a):  # 조용히
            pass

        def _json(self, code: int, obj: dict) -> None:
            data = json.dumps(obj, ensure_ascii=False).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(data)

        def r_health(self) -> None:
            self._json(200, {"app": "llmwiki", "root": str(root), "pid": os.getpid(), "port": self.server.server_address[1]})

        def r_stop(self) -> None:
            if self.headers.get("X-Llmwiki-Token") != token:
                self._json(403, {"error": "token"})
                return
            self._json(200, {"stopping": True})
            threading.Thread(target=self.server.shutdown, daemon=True).start()

        def r_ask(self) -> None:
            # TODO(나중에): 학생 본인 ChatGPT 로그인으로 `codex exec`를 불러 답을 돌려주는 자리.
            #   붙일 때 지킬 것: 127.0.0.1만, Origin/Host 확인 + 토큰, 작업 폴더 안에서만 실행, 시간 제한·동시 1건,
            #   유료 API 키 금지, 사용자 ~/.codex 설정은 읽기만. 지금은 의도적으로 501을 돌려준다.
            self._json(501, {"error": "not_implemented",
                             "message": "아직 준비 중이에요. 💬 Codex에게 물어보기 버튼으로 복사해서 Codex 채팅에 붙여넣으세요."})

        ROUTES = {("GET", HEALTH): "r_health", ("POST", STOP): "r_stop", ("POST", "/api/ask"): "r_ask"}

        def _route(self, method: str) -> bool:
            name = self.ROUTES.get((method, self.path.split("?", 1)[0]))
            if name:
                getattr(self, name)()
                return True
            return False

        def do_GET(self):  # noqa: N802
            if not self._route("GET"):
                super().do_GET()

        def do_HEAD(self):  # noqa: N802
            super().do_HEAD()

        def do_POST(self):  # noqa: N802
            if not self._route("POST"):
                self._json(404, {"error": "not_found"})

        def end_headers(self):
            if not self.path.startswith("/__llmwiki__"):
                self.send_header("Cache-Control", "no-cache")  # 다시 만든 화면이 바로 보이게
            super().end_headers()

    Handler.extensions_map = {**http.server.SimpleHTTPRequestHandler.extensions_map,
                              ".js": "text/javascript; charset=utf-8", ".json": "application/json; charset=utf-8",
                              ".html": "text/html; charset=utf-8", ".css": "text/css; charset=utf-8"}

    class Server(socketserver.ThreadingMixIn, http.server.HTTPServer):
        daemon_threads = True
        # macOS/Linux: 방금 끈 서버의 TIME_WAIT 때문에 같은 포트를 못 쓰는 일 방지(두 서버가 같은 포트를 듣지는 못함).
        # Windows: SO_REUSEADDR는 남의 포트까지 가로챌 수 있어 끈다.
        allow_reuse_address = os.name != "nt"

    httpd = None
    for port in range(start_port, start_port + TRIES):
        try:
            httpd = Server(("127.0.0.1", port), functools.partial(Handler, directory=str(site)))
            break
        except OSError:
            continue
    if httpd is None:
        return 3
    port = httpd.server_address[1]
    sp = state_path(root)
    sp.parent.mkdir(parents=True, exist_ok=True)
    sp.write_text(json.dumps({"pid": os.getpid(), "port": port, "token": token, "root": str(root),
                              "started": time.strftime("%Y-%m-%d %H:%M:%S")}, ensure_ascii=False), encoding="utf-8")
    try:
        httpd.serve_forever(poll_interval=0.5)
    finally:
        httpd.server_close()
        st = read_state(root)
        if st and st.get("pid") == os.getpid():
            try:
                sp.unlink()
            except OSError:
                pass
    return 0


# ------------------------------------------------------------------ 시작·끄기
def _spawn(root: Path, port: int) -> subprocess.Popen:
    tools = str(Path(__file__).resolve().parent.parent)
    env = dict(os.environ)
    env["PYTHONPATH"] = tools + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
    env["PYTHONUTF8"] = "1"
    py = sys.executable
    cmd_tail = ["-m", "llmwiki.serve", "--worker", "--root", str(root), "--port", str(port)]
    logf = open(root / ".llmwiki" / "serve.log", "ab")  # noqa: SIM115 — 자식에게 넘김
    kw: dict[str, Any] = {"cwd": str(root), "env": env, "stdin": subprocess.DEVNULL, "stdout": logf, "stderr": logf, "close_fds": True}
    if os.name == "nt":
        pyw = Path(py).with_name("pythonw.exe")
        if pyw.exists():
            py = str(pyw)
        flags = 0x00000008 | 0x00000200  # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP
        try:
            return subprocess.Popen([py, *cmd_tail], creationflags=flags | 0x01000000, **kw)  # + CREATE_BREAKAWAY_FROM_JOB
        except OSError:
            return subprocess.Popen([py, *cmd_tail], creationflags=flags, **kw)  # 작업 개체가 분리를 막으면
    return subprocess.Popen([py, *cmd_tail], start_new_session=True, **kw)


def start(root: Path, port: int = DEFAULT_PORT, wait: float = 8.0) -> dict[str, Any]:
    cur = running(root)
    if cur:
        return {"ok": True, "reused": True, **cur}
    (root / ".llmwiki").mkdir(exist_ok=True)
    try:
        state_path(root).unlink()
    except OSError:
        pass
    proc = _spawn(root, port)
    t0 = time.time()
    while time.time() - t0 < wait:
        st = read_state(root)
        if st and st.get("pid") == proc.pid and _same_root(health(st["port"]), root):
            return {"ok": True, "reused": False, "port": st["port"], "pid": proc.pid, "url": f"http://127.0.0.1:{st['port']}/"}
        if proc.poll() is not None:
            break
        time.sleep(0.2)
    rc = proc.poll()
    reason = f"서버가 바로 멈췄어요(rc={rc})" if rc is not None else "응답이 없어요(시간 초과)"
    if rc == 3:
        reason = f"포트 {port}–{port + TRIES - 1}가 모두 사용 중이에요"
    return {"ok": False, "reason": reason + " · 자세한 내용: .llmwiki/serve.log"}


def stop(root: Path) -> dict[str, Any]:
    cur = running(root)
    st = read_state(root) or {}
    if not cur:
        try:
            state_path(root).unlink()
        except OSError:
            pass
        return {"ok": True, "was_running": False}
    try:
        req = urllib.request.Request(f"http://127.0.0.1:{cur['port']}{STOP}", data=b"{}", method="POST",
                                     headers={"X-Llmwiki-Token": st.get("token", "")})
        urllib.request.urlopen(req, timeout=2).read()  # noqa: S310 — localhost
    except Exception:  # noqa: BLE001
        pid = cur.get("pid")
        if pid:
            try:
                if os.name == "nt":
                    subprocess.run(["taskkill", "/PID", str(pid), "/F"], capture_output=True, check=False)
                else:
                    import signal
                    os.kill(int(pid), signal.SIGTERM)
            except Exception:  # noqa: BLE001
                pass
    for _ in range(25):
        if not health(cur["port"], timeout=0.3):
            break
        time.sleep(0.2)
    try:
        state_path(root).unlink()
    except OSError:
        pass
    return {"ok": health(cur["port"], timeout=0.3) is None, "was_running": True, "port": cur["port"]}


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--worker", action="store_true")
    ap.add_argument("--root", required=True)
    ap.add_argument("--port", type=int, default=DEFAULT_PORT)
    a = ap.parse_args()
    sys.exit(_worker(Path(a.root).resolve(), a.port) if a.worker else 2)
