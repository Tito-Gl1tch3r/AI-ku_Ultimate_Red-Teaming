# -*- coding: utf-8 -*-
"""
深度挖掘：关系演化 / 星期×小时热力图 / 关键词指纹 / 链接域名 / @图谱 / 回复时延 / 夜猫子 / 爆发日
  python deep_analyze.py --json export/wechat_messages.json --outdir deep_insights
  可选: --self-name "我的昵称" --top 15 --userdict my_words.txt
依赖: jieba (pip install jieba)
输出: deep_insights.json + 关系演化_年度矩阵.json + 热力图_星期小时.txt，并把全部洞察打印到 stdout
"""
import argparse, collections, datetime, json, os, re

SELF_LABEL = "我"


def main():
    ap = argparse.ArgumentParser(description="微信聊天记录深度挖掘")
    ap.add_argument("--json", required=True)
    ap.add_argument("--outdir", required=True)
    ap.add_argument("--self-name", default=None, help="登录账号的显示名（用于关键词区分我方/对方，默认不区分）")
    ap.add_argument("--top", type=int, default=15, help="单聊 Top N（默认15）")
    ap.add_argument("--userdict", default=None, help="jieba 自定义词表（每行一个词），用于业务词")
    args = ap.parse_args()
    os.makedirs(args.outdir, exist_ok=True)
    if args.self_name:
        global SELF_LABEL
        SELF_LABEL = args.self_name

    print("[load]")
    with open(args.json, encoding="utf-8") as f:
        msgs = json.load(f)

    # ---------- 1. 关系演化：Top单聊 × 年度矩阵 ----------
    direct = collections.defaultdict(list)
    for m in msgs:
        if not m.get("is_group_chat") and m.get("ts"):
            direct[m.get("chat_room") or "?"].append(m)
    top_direct = [c for c, _ in sorted(direct.items(), key=lambda kv: -len(kv[1]))[:args.top]]
    year_matrix = {}
    for name in top_direct:
        yc = collections.Counter(datetime.datetime.fromtimestamp(m["ts"]).year for m in direct[name])
        year_matrix[name] = {str(y): c for y, c in sorted(yc.items())}
    with open(os.path.join(args.outdir, "关系演化_年度矩阵.json"), "w", encoding="utf-8") as f:
        json.dump(year_matrix, f, ensure_ascii=False, indent=1)
    print("\n=== Top%d 单聊 年度演化 ===" % args.top)
    for name in top_direct:
        ys = list(year_matrix[name])
        tail = " ".join(f"{y}:{year_matrix[name][y]}" for y in ys[-5:])
        print(f"  {name}: {len(direct[name])}条 | 活跃{len(ys)}年 [{ys[0]}→{ys[-1]}] {tail}")

    # ---------- 2. 星期×小时热力图 ----------
    heat = collections.Counter()
    for m in msgs:
        dt = datetime.datetime.fromtimestamp(m["ts"])
        heat[(dt.strftime("%a"), dt.hour)] += 1
    WD = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    WD_CN = {"Mon": "一", "Tue": "二", "Wed": "三", "Thu": "四", "Fri": "五", "Sat": "六", "Sun": "日"}
    with open(os.path.join(args.outdir, "热力图_星期小时.txt"), "w", encoding="utf-8") as f:
        f.write("      " + " ".join(f"{h:>4d}" for h in range(24)) + "\n")
        for wd in WD:
            f.write(f"周{WD_CN[wd]}  " + " ".join(f"{heat.get((wd, h), 0):>4d}" for h in range(24)) + "\n")
    print("\n=== 热力图 Top10 (星期,小时) ===")
    for (wd, h), c in heat.most_common(10):
        print(f"  周{WD_CN[wd]} {h:02d}点: {c}")

    # ---------- 3. 关键词指纹（对方发的文本，反映关系内容） ----------
    import jieba
    if args.userdict and os.path.exists(args.userdict):
        jieba.load_userdict(args.userdict)
    STOP = set("的了是在我有和你这那就不都也人要会被把吗呢吧啊呀哦嗯哈诶呗啦喽咯哇嘻嘻嗯嗯好的收到哦哦行哦好嗯呢"
               "一个什么怎么这个那个我们你们他们自己大家可能应该如果因为所以但是然后还是就是已经现在昨天今天明天"
               "时候刚才刚刚等等先再又还就很挺太更最比较真有点儿上上下下来去出来进去回家公司在说看看想想知道觉得"
               "可以没有今天现在一下你们咱们不是还是觉得其实真的确实应该可能这样那样这里那里他们你们大家过来出去"
               "多少直接一定一起马上马上等一下晚点回头下次上次之前以后后来然后接着另外其他有些一点几个第一第二".split())

    def is_self(m):
        if args.self_name:
            return bool(m.get("is_self")) or m.get("sender") == args.self_name
        return bool(m.get("is_self"))

    def keywords(ms, topn=25):
        words = collections.Counter()
        for m in ms:
            if m.get("msg_type") != 1 or is_self(m):
                continue
            txt = m.get("content") or ""
            if len(txt) > 500 or (txt.startswith("[") and "]" in txt[:8]):
                continue
            for w in jieba.cut(txt):
                w = w.strip()
                if len(w) >= 2 and not re.match(r"^[\d\W_]+$", w) and w not in STOP:
                    words[w] += 1
        return words.most_common(topn)

    print("\n=== 全局关键词 Top25（对方发的文本） ===")
    kw_all = keywords(msgs)
    print("  " + " ".join(f"{w}:{c}" for w, c in kw_all))
    kw_by = {name: keywords(direct.get(name, []), 15) for name in top_direct[:5]}
    for name, kws in kw_by.items():
        print(f"  [{name}] " + " ".join(f"{w}:{c}" for w, c in kws))

    # ---------- 4. 链接域名 ----------
    domain_c = collections.Counter()
    url_re = re.compile(r"https?://([^/\s\"'<>]+)")
    for m in msgs:
        txt = str(m.get("content") or "")
        if "http" in txt:
            for d in url_re.findall(txt):
                domain_c[d.lower()] += 1
    print("\n=== 链接域名 Top15 ===")
    for d, c in domain_c.most_common(15):
        print(f"  {d}: {c}")

    # ---------- 5. @图谱 ----------
    at_re = re.compile(r"@([\w\u4e00-\u9fa5\-]{2,20})")
    at_pairs = collections.Counter()
    for m in msgs:
        if m.get("is_group_chat") and m.get("msg_type") == 1:
            sender = m.get("sender")
            for target in at_re.findall(m.get("content") or ""):
                if target != sender:
                    at_pairs[(sender, target)] += 1
    print("\n=== @图谱 Top15 ===")
    for (s, t), c in at_pairs.most_common(15):
        print(f"  {s} → {t}: {c}")

    # ---------- 6. 回复时延（单聊双向中位数） ----------
    def reply_latency(name):
        ms = sorted(direct.get(name, []), key=lambda m: m["ts"])
        lags_me, lags_them = [], []
        for prev, cur in zip(ms, ms[1:]):
            if is_self(prev) == is_self(cur):
                continue
            lag = cur["ts"] - prev["ts"]
            if 2 <= lag <= 3600:
                (lags_me if is_self(cur) else lags_them).append(lag)
        med = lambda xs: sorted(xs)[len(xs) // 2] if xs else None
        return len(lags_me), med(lags_me), len(lags_them), med(lags_them)

    print("\n=== 回复时延中位数（秒） ===")
    for name in top_direct[:8]:
        nm, lm, nt, lt = reply_latency(name)
        if nm or nt:
            fmt = lambda s: f"{int(s)//60}m{int(s)%60:02d}s" if s and s >= 60 else (f"{s:.0f}s" if s else "-")
            print(f"  {name}: 我→{fmt(lm)}(n={nm}) 对方→{fmt(lt)}(n={nt})")

    # ---------- 7. 文本长度 ----------
    lens = sorted(len(m.get("content") or "") for m in msgs if m.get("msg_type") == 1)
    if lens:
        pct = lambda p: lens[int(len(lens) * p)]
        print(f"\n=== 文本长度 === n={len(lens)} 中位={pct(0.5)} P90={pct(0.9)} P99={pct(0.99)} max={lens[-1]}")

    # ---------- 8. 夜猫子（凌晨0-6点） ----------
    night = collections.Counter()
    for m in msgs:
        if 0 <= datetime.datetime.fromtimestamp(m["ts"]).hour < 6:
            night[m.get("chat_room") or "?"] += 1
    print("\n=== 凌晨0-6点 Top8 会话 ===")
    for r, c in night.most_common(8):
        print(f"  {r}: {c}")

    # ---------- 9. 单日爆发 ----------
    day_c = collections.Counter()
    for m in msgs:
        day_c[datetime.datetime.fromtimestamp(m["ts"]).strftime("%Y-%m-%d")] += 1
    avg = sum(day_c.values()) / len(day_c)
    print("\n=== 单日爆发 Top10（日均 %d） ===" % avg)
    for d, c in day_c.most_common(10):
        print(f"  {d} 周{WD_CN[datetime.date.fromisoformat(d).strftime('%a')]}: {c} ({c / avg:.0f}x)")

    result = {
        "kw_all": kw_all, "kw_by_person": kw_by,
        "top_domains": domain_c.most_common(30),
        "at_graph": [{"from": s, "to": t, "count": c} for (s, t), c in at_pairs.most_common(60)],
        "year_matrix": year_matrix,
        "heat_top": [{"wd": w, "hour": h, "count": c} for (w, h), c in heat.most_common(30)],
        "night_top": night.most_common(15),
        "burst_days": day_c.most_common(15),
    }
    with open(os.path.join(args.outdir, "deep_insights.json"), "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=1)
    print("\n[saved]", args.outdir)


if __name__ == "__main__":
    main()
