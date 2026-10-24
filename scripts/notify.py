#!/usr/bin/env python3
"""Create/update GitHub Issues for new direct Agent ID leads, with URL dedup."""
import argparse
import json
import os
from pathlib import Path
import sys
from urllib.request import Request, urlopen
from urllib.parse import quote
from scout import official

BASE="https://api.github.com"

def api(method, path, token, payload=None):
    body=None if payload is None else json.dumps(payload).encode("utf-8")
    req=Request(BASE+path, data=body, method=method, headers={
        "Authorization":"Bearer "+token, "Accept":"application/vnd.github+json",
        "X-GitHub-Api-Version":"2022-11-28", "Content-Type":"application/json",
        "User-Agent":"agent-id-hunter-community"})
    with urlopen(req, timeout=20) as resp:
        return json.loads(resp.read(1_000_000).decode("utf-8"))

def notify(items, repo, token, request=api, limit=5):
    if not repo or "/" not in repo or any(x in repo for x in ("..", " ", "?", "#")):
        raise ValueError("无效 GITHUB_REPOSITORY")
    repo=quote(repo, safe="/")
    targets=[i for i in items if i.get("kind")=="direct" and i.get("change") in ("new", "changed") and official(i.get("url",""))]
    if not targets: return {"created":0,"updated":0,"ignored":0}
    issues=[]
    for page in range(1,6):
        batch=request("GET",f"/repos/{repo}/issues?state=all&per_page=100&page={page}",token)
        issues.extend(i for i in batch if "pull_request" not in i)
        if len(batch)<100: break
    created=updated=ignored=0
    for i in targets[:limit]:
        marker="<!-- agent-id-hunter-url:"+i["id"]+" -->"
        fingerprint="<!-- agent-id-hunter-fingerprint:"+i.get("hash","")+"-"+i["title"][:30]+" -->"
        match=next((x for x in issues if marker in (x.get("body") or "")),None)
        if match is None:
            body="\n".join(["**自动发现的待核验页面线索**，不是活动资格或奖励承诺。",
                           "", "原始链接："+i["url"], "线索来源："+i.get("source",""),
                           "", "- [ ] 确认发布者和官宣活动细则",
                           "- [ ] 确认是否真的要求持有 .ai，以及哪个钱包算数",
                           "- [ ] 核对报名、计数、证据、截止和领奖", "", marker, fingerprint])
            result=request("POST",f"/repos/{repo}/issues",token,
                           {"title":"[待核实 Agent ID 线索] "+i["title"][:90],"body":body})
            issues.append(result)
            created+=1
        elif i["change"]=="changed":
            issue_number=match["number"]
            comments=request("GET",f"/repos/{repo}/issues/{issue_number}/comments?per_page=100",token)
            if fingerprint not in (match.get("body") or "") and not any(fingerprint in (c.get("body") or "") for c in comments):
                request("POST",f"/repos/{repo}/issues/{issue_number}/comments",token,
                        {"body":"自动扫描发现页面内容或标题变化，请复核官方原文："+i["url"]+"\n\n"+fingerprint})
                updated+=1
            else: ignored+=1
        else: ignored+=1
    return {"created":created,"updated":updated,"ignored":ignored}

def main(argv=None):
    p=argparse.ArgumentParser()
    p.add_argument("--input",type=Path,required=True)
    args=p.parse_args(argv)
    token=os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    repo=os.environ.get("GITHUB_REPOSITORY")
    if not token or not repo:
        print("缺少 GitHub Actions token/repo",file=sys.stderr); return 2
    try:
        data=json.loads(args.input.read_text(encoding="utf-8"))
        print(json.dumps(notify(data["items"],repo,token),ensure_ascii=False))
        return 0
    except (OSError,ValueError,KeyError,json.JSONDecodeError) as e:
        print("Issue 提醒失败："+str(e),file=sys.stderr); return 1
if __name__=="__main__":
    sys.exit(main())
