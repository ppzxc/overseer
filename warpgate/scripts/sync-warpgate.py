#!/usr/bin/env python3
"""targets.json(원하는 상태)을 Warpgate Admin API에 멱등 반영한다. 표준 라이브러리만 사용.

사용: WARPGATE_ADMIN_PASSWORD=... sync-warpgate.py [--config targets.json] [--dry-run]
삭제는 하지 않는다. 대상↔역할, 사용자↔역할 연결은 설정에 명시된 역할/대상 범위에서만 맞춘다.
"""
import argparse, json, os, ssl, sys, urllib.error, urllib.request

ADMIN = "/@warpgate/admin/api"


class Client:
    def __init__(self, base, insecure, host=None):
        self.base = base.rstrip("/")
        self.host = host  # 세션이 Host 헤더에 묶이므로 IP로 접속할 때 external_host를 지정
        self.ctx = ssl.create_default_context()
        if insecure:
            self.ctx.check_hostname = False
            self.ctx.verify_mode = ssl.CERT_NONE
        self.cookie = ""

    def call(self, method, path, body=None, ok=(200, 201, 204)):
        req = urllib.request.Request(
            self.base + path, method=method,
            data=None if body is None else json.dumps(body).encode(),
            headers={"Content-Type": "application/json",
                     **({"Host": self.host} if self.host else {}),
                     **({"Cookie": self.cookie} if self.cookie else {})})
        try:
            r = urllib.request.urlopen(req, timeout=30, context=self.ctx)
            cookies = [c.split(";")[0] for c in r.headers.get_all("Set-Cookie") or []]
            if cookies:
                self.cookie = "; ".join(cookies)
            raw = r.read().decode()
            status = r.status
        except urllib.error.HTTPError as e:
            status, raw = e.code, e.read().decode()[:300]
        if status not in ok:
            raise SystemExit(f"{method} {path} -> {status}: {raw}")
        try:
            return json.loads(raw) if raw else None
        except ValueError:
            return None


def target_options(t):
    kind = t["kind"]
    auth = {"kind": "Password", "password": t["password"]}
    if kind == "ssh":
        return {"kind": "Ssh", "host": t["host"], "port": t.get("port", 22), "username": t["username"],
                "allow_insecure_algos": t.get("allow_insecure_algos", False), "auth": auth}
    tls = {"mode": t.get("tls", "Required"), "verify": t.get("tls_verify", True)}
    if kind == "postgres":
        return {"kind": "Postgres", "host": t["host"], "port": t.get("port", 5432), "username": t["username"],
                "auth": auth, "tls": tls, "protocol_version": "3.0",
                "default_database_name": t.get("database", "postgres")}
    if kind in ("mysql", "mariadb"):
        return {"kind": "MySql", "host": t["host"], "port": t.get("port", 3306), "username": t["username"],
                "auth": auth, "tls": tls}
    raise SystemExit(f"지원하지 않는 kind: {kind} (target {t['name']})")


def subset(want, have):
    """want의 모든 값이 have에 같은 값으로 있으면 True (서버가 채우는 기본값은 무시)."""
    if isinstance(want, dict):
        return isinstance(have, dict) and all(k in have and subset(v, have[k]) for k, v in want.items())
    return want == have


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=os.path.join(os.path.dirname(__file__), "..", "targets.json"))
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    cfg = json.load(open(a.config))
    url = os.environ.get("WARPGATE_URL", "https://127.0.0.1:8888")
    pw = os.environ.get("WARPGATE_ADMIN_PASSWORD") or sys.exit("WARPGATE_ADMIN_PASSWORD 필요")
    c = Client(url, os.environ.get("WARPGATE_INSECURE_TLS", "").lower() == "true",
               os.environ.get("WARPGATE_HOST_HEADER"))
    c.call("POST", "/@warpgate/api/auth/login",
           {"username": os.environ.get("WARPGATE_ADMIN_USER", "admin"), "password": pw})
    dry = a.dry_run

    def act(msg, fn):
        print(("[dry-run] " if dry else "") + msg)
        return None if dry else fn()

    # 대상
    have = {t["name"]: t for t in c.call("GET", ADMIN + "/targets")}
    base = {"ticket_requests_disabled": False, "ticket_require_approval": False}
    tid = {}
    for t in cfg.get("targets", []):
        body = {**base, "require_approval": t.get("require_approval", False),
                "name": t["name"], "options": target_options(t)}
        cur = have.get(t["name"])
        if cur is None:
            r = act(f"대상 생성: {t['name']}", lambda b=body: c.call("POST", ADMIN + "/targets", b))
            tid[t["name"]] = r and r["id"]
        else:
            tid[t["name"]] = cur["id"]
            if not subset({"options": body["options"], "require_approval": body["require_approval"]}, cur):
                merged = {k: v for k, v in cur.items() if k not in ("id", "allow_roles")}
                merged["options"] = {**cur["options"], **body["options"]}
                merged["require_approval"] = body["require_approval"]
                act(f"대상 갱신: {t['name']}",
                    lambda i=cur["id"], b=merged: c.call("PUT", f"{ADMIN}/targets/{i}", b))

    # 역할 + 대상 연결
    roles = {r["name"]: r["id"] for r in c.call("GET", ADMIN + "/roles")}
    for rname, tnames in cfg.get("roles", {}).items():
        if rname not in roles:
            r = act(f"역할 생성: {rname}", lambda n=rname: c.call("POST", ADMIN + "/roles", {"name": n}))
            roles[rname] = r and r["id"]
    for t in cfg.get("targets", []):
        if not tid.get(t["name"]):
            continue
        linked = {r["id"] for r in c.call("GET", f"{ADMIN}/targets/{tid[t['name']]}/roles")}
        for rname, tnames in cfg.get("roles", {}).items():
            rid = roles.get(rname)
            if not rid:
                continue
            want = t["name"] in tnames
            if want and rid not in linked:
                act(f"연결: 대상 {t['name']} ← 역할 {rname}",
                    lambda i=tid[t["name"]], r=rid: c.call("POST", f"{ADMIN}/targets/{i}/roles/{r}"))
            elif not want and rid in linked:
                act(f"해제: 대상 {t['name']} ✕ 역할 {rname}",
                    lambda i=tid[t["name"]], r=rid: c.call("DELETE", f"{ADMIN}/targets/{i}/roles/{r}"))

    # 사용자 + 역할 + 공개키
    users = {u["username"]: u["id"] for u in c.call("GET", ADMIN + "/users")}
    for uname, spec in cfg.get("users", {}).items():
        if uname not in users:
            r = act(f"사용자 생성: {uname}", lambda n=uname: c.call("POST", ADMIN + "/users", {"username": n}))
            users[uname] = r and r["id"]
        uid = users[uname]
        if not uid:
            continue
        linked = {r["id"] for r in c.call("GET", f"{ADMIN}/users/{uid}/roles")}
        for rname, rid in roles.items():
            if rname not in cfg.get("roles", {}):
                continue  # 관리 범위 밖 역할은 건드리지 않음
            want = rname in spec.get("roles", [])
            if want and rid not in linked:
                act(f"연결: 사용자 {uname} ← 역할 {rname}",
                    lambda r=rid: c.call("POST", f"{ADMIN}/users/{uid}/roles/{r}"))
            elif not want and rid in linked:
                act(f"해제: 사용자 {uname} ✕ 역할 {rname}",
                    lambda r=rid: c.call("DELETE", f"{ADMIN}/users/{uid}/roles/{r}"))
        have_keys = {k["label"] for k in c.call("GET", f"{ADMIN}/users/{uid}/credentials/public-keys")}
        for label, key in spec.get("public_keys", {}).items():
            if label not in have_keys:
                act(f"공개키 등록: {uname}/{label}",
                    lambda l=label, k=key: c.call("POST", f"{ADMIN}/users/{uid}/credentials/public-keys",
                                                  {"label": l, "openssh_public_key": k}))
    print("완료")


if __name__ == "__main__":
    main()
