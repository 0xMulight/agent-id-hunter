#!/usr/bin/env python3
"""Read-only scanner for official Agent ID leads. Python stdlib only."""
import argparse
import hashlib
from html.parser import HTMLParser
import html
import json
from pathlib import Path
import re
import sys
from datetime import datetime, timezone
from urllib.parse import urljoin, urlsplit, urlunsplit, parse_qsl, urlencode
from urllib.request import Request, urlopen, HTTPRedirectHandler, build_opener

ROOT = Path(__file__).resolve().parents[1]
ALLOWED = ("binance.com", "bnbchain.org", "space.id", "four.meme")
DIRECT = re.compile(r"(?i)(?:\bagent[\s-]?id\b|#?myagentid\b|(?<![a-z])\.ai\b)")
ECOSYSTEM = re.compile(r"(?i)(?:\bagentic\b|\bai[\s-]?agent\b|\bERC[\s-]?8004\b|\bBAP[\s-]?578\b|agentic wallet)")
MAX_BYTES = 1_200_000

def official(url):
    p = urlsplit(url)
    host = (p.hostname or "").lower()
    return p.scheme == "https" and not p.username and not p.password and p.port in (None, 443) and any(host == h or host.endswith("." + h) for h in ALLOWED)

def normalized_url(url):
    u = urlsplit(url)
    q = urlencode([(k, v) for k, v in parse_qsl(u.query, keep_blank_values=True) if not k.lower().startswith("utm_")])
    return urlunsplit((u.scheme, u.netloc.lower(), u.path.rstrip("/") or "/", q, ""))

def digest(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()

class OfficialOnlyRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if not official(newurl):
            raise ValueError("官方页面跳转至非白名单域名，已拒绝")
        return super().redirect_request(req, fp, code, msg, headers, newurl)

def fetch(url):
    if not official(url):
        raise ValueError("只允许读取预设的官方 HTTPS 域名")
    opener = build_opener(OfficialOnlyRedirect())
    req = Request(url, headers={"User-Agent": "AgentIDHunter/0.5 (open-source research)", "Accept": "text/html"})
    with opener.open(req, timeout=15) as response:
        if not official(response.geturl()):
            raise ValueError("跳转后地址无效")
        content_type = response.headers.get("Content-Type", "")
        if "text/html" not in content_type and "text/plain" not in content_type:
            raise ValueError("页面不是 HTML")
        data = response.read(MAX_BYTES + 1)
        if len(data) > MAX_BYTES:
            raise ValueError("页面超过大小限制")
        return data.decode(response.headers.get_content_charset() or "utf-8", errors="replace")

class Parse(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.ignore = 0
        self.in_title = False
        self.anchor = None
        self.links = []
        self.title = []
        self.body = []
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag in ("script", "style", "noscript", "svg", "template"):
            self.ignore += 1
            return
        if self.ignore:
            return
        if tag == "title": self.in_title = True
        if tag == "a": self.anchor = (attrs.get("href", ""), [])
    def handle_endtag(self, tag):
        if tag in ("script", "style", "noscript", "svg", "template") and self.ignore:
            self.ignore -= 1
            return
        if self.ignore: return
        if tag == "title": self.in_title = False
        if tag == "a" and self.anchor is not None:
            href, parts = self.anchor
            name = collapse(" ".join(parts))
            if href and name: self.links.append((href, name))
            self.anchor = None
    def handle_data(self, text):
        if self.ignore: return
        self.body.append(text)
        if self.in_title: self.title.append(text)
        if self.anchor is not None: self.anchor[1].append(text)

def collapse(value):
    return re.sub(r"\s+", " ", html.unescape(value)).strip()

def parse(raw):
    p = Parse()
    p.feed(raw)
    return {"title": collapse(" ".join(p.title)), "text": collapse(" ".join(p.body)), "links": p.links}

def classify(text):
    if DIRECT.search(text): return "direct"
    if ECOSYSTEM.search(text): return "ecosystem"
    return None

def make_item(url, label, origin, text=""):
    url = normalized_url(url)
    kind = classify(label)
    if not kind: return None
    return {"id": digest(url)[:16], "url": url, "title": label[:220],
            "kind": kind, "source": origin, "hash": digest(text[:15000]) if text else "",
            "warning": "只是一条线索，必须打开原文核查是否真有 .ai 持有门槛"}

def collect(sources, fetch_fn=fetch):
    items, diagnostics = {}, []
    for s in sources:
        url, kind, name = s["url"], s.get("kind", "index"), s.get("name", s["url"])
        if not official(url):
            diagnostics.append({"name": name, "ok": False, "error": "未获授权的来源域名"})
            continue
        try:
            p = parse(fetch_fn(url))
            found = []
            if kind == "page":
                c = make_item(url, p["title"] or name, name, p["text"])
                if c: found.append(c)
            else:
                for link, label in p["links"]:
                    absolute = urljoin(url, link)
                    if not official(absolute): continue
                    if "/square/" in urlsplit(absolute).path: continue
                    c = make_item(absolute, label, name)
                    if c: found.append(c)
            for c in found: items[c["id"]] = c
            diagnostics.append({"name": name, "ok": True, "hits": len(found),
                                "note": "动态加载或反爬可能导致漏检" if not p["links"] and kind == "index" else ""})
        except Exception as e:
            diagnostics.append({"name": name, "ok": False, "error": str(e)[:180]})
    return list(items.values()), diagnostics

def compare(items, previous):
    old = previous.get("items", {})
    initial = not previous.get("scanned")
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    merged = dict(old)
    for i in items:
        before = old.get(i["id"])
        if not before:
            i["change"] = "baseline" if initial else "new"
        elif i["title"] != before.get("title") or (i["hash"] and i["hash"] != before.get("hash")):
            i["change"] = "changed"
        else:
            i["change"] = "same"
        merged[i["id"]] = {"title": i["title"], "hash": i["hash"], "url": i["url"], "seen_at": now}
    return {"scanned": True, "scanned_at": now, "items": merged}, items

def report(items, diagnostics):
    ts = datetime.now(timezone.utc).isoformat(timespec="minutes")
    lines = [f"# Agent ID Hunter 扫描报告 ({ts})", "",
             "**仅为官方页面上的线索，不代表已官宣活动、持有资格或空投资格。**", ""]
    changes = [i for i in items if i["change"] != "same"]
    lines.append(f"共发现 {len(items)} 条候选链接，本次新增/变更/首次建档 {len(changes)} 条。")
    for i in changes[:40]:
        lines.extend(["", f"## {i['title']}", f"- 分类：{i['kind']}",
                      f"- 变化：{i['change']}", f"- 来源：{i['source']}",
                      f"- 链接：{i['url']}",
                      "- 待核实：.ai 是否为强制资格、持有权、钱包/报名/任务计数/领奖"])
    if not changes:
        lines += ["", "未发现新线索；**不等于没有活动**。动态站点、X 和 App 内活动可能漏检。"]
    lines += ["", "## 来源状态"]
    for d in diagnostics:
        lines.append(f"- {d['name']}: " + (f"读取成功（候选 {d['hits']}）{d.get('note', '')}" if d["ok"] else "读取失败：" + d["error"]))
    return "\n".join(lines) + "\n"

def write(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(content, encoding="utf-8")
    temp.replace(path)

def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("command", nargs="?", default="scan", choices=["scan"])
    ap.add_argument("--config", type=Path, default=ROOT/"config/sources.json")
    ap.add_argument("--state", type=Path, default=ROOT/"data/watch-state.json")
    ap.add_argument("--report", type=Path, default=ROOT/"data/latest-report.md")
    ap.add_argument("--json", type=Path, default=ROOT/"data/latest-items.json")
    a = ap.parse_args(argv)
    try:
        sources = json.loads(a.config.read_text(encoding="utf-8"))["sources"]
        items, diagnostics = collect(sources)
        if not any(d["ok"] for d in diagnostics):
            print("所有来源都失败；不更新上次状态，也不能据此判定没有活动", file=sys.stderr)
            return 2
        previous = json.loads(a.state.read_text(encoding="utf-8")) if a.state.exists() else {}
        new_state, items = compare(items, previous)
        write(a.state, json.dumps(new_state, ensure_ascii=False, indent=2) + "\n")
        write(a.report, report(items, diagnostics))
        write(a.json, json.dumps({"items": items, "diagnostics": diagnostics}, ensure_ascii=False, indent=2) + "\n")
        print(f"官方来源成功 {sum(bool(d['ok']) for d in diagnostics)}/{len(diagnostics)}；候选 {len(items)}；报告：{a.report}")
        if any(not d["ok"] for d in diagnostics): print("注意：有来源读取失败，报告不完整")
        return 0
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as e:
        print(f"失败：{e}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    sys.exit(main())
