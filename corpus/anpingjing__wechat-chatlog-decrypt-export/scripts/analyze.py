# -*- coding: utf-8 -*-
"""
微信聊天记录多维分析
  全账号模式: python analyze.py --json export/wechat_messages.json --outdir analysis
  单群模式:   python analyze.py --json export/wechat_messages.json --outdir analysis --group "群名"
输出: summary.json + 各维度 CSV（+ 单群模式额外输出该群全量消息 JSON）
"""
import argparse, collections, csv, datetime, json, os, sys

TYPE_LABEL = {
    1: "文本", 3: "图片", 34: "语音", 43: "视频", 47: "表情", 48: "位置",
    49: "链接/文件/名片", 50: "音视频通话", 51: "状态提示", 10000: "系统消息",
    10002: "撤回/系统", 42: "名片",
}
HOUR_BINS = [(0, 6, "凌晨0-6点"), (6, 9, "早6-9点"), (9, 12, "上午9-12点"),
             (12, 14, "午间12-14点"), (14, 18, "下午14-18点"),
             (18, 22, "晚上18-22点"), (22, 24, "深夜22-24点")]
WD_ORDER = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
WD_CN = {"Mon": "周一", "Tue": "周二", "Wed": "周三", "Thu": "周四",
         "Fri": "周五", "Sat": "周六", "Sun": "周日"}


def dump_csv(outdir, name, rows):
    if not rows:
        return
    with open(os.path.join(outdir, name), "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)


def silence_gaps(day_counter, top=3):
    """连续无消息的最长区间（识别休眠-复活节奏）"""
    if not day_counter:
        return []
    days = set(day_counter)
    d0 = datetime.date.fromisoformat(min(days))
    d1 = datetime.date.fromisoformat(max(days))
    gaps, cur, d = [], None, d0
    while d <= d1:
        k = d.isoformat()
        if k not in days:
            cur = cur or [k, k]
            cur[1] = k
        elif cur:
            gaps.append(cur)
            cur = None
        d += datetime.timedelta(days=1)
    if cur:
        gaps.append(cur)
    gaps.sort(key=lambda g: (datetime.date.fromisoformat(g[1]) -
                             datetime.date.fromisoformat(g[0])).days, reverse=True)
    return gaps[:top]


def analyze_all(msgs, outdir):
    conv_meta, type_c, year_c, month_c = {}, collections.Counter(), collections.Counter(), collections.Counter()
    hour_c, wd_c, bin_c = collections.Counter(), collections.Counter(), collections.Counter()
    sender_in_groups = collections.Counter()
    self_total, n = 0, len(msgs)
    for m in msgs:
        dt = datetime.datetime.fromtimestamp(m["ts"])
        cid = m.get("conversation_id", "?")
        is_self = bool(m.get("is_self"))
        mt = m.get("msg_type")
        type_c[mt] += 1
        year_c[dt.year] += 1
        month_c[f"{dt.year:04d}-{dt.month:02d}"] += 1
        hour_c[dt.hour] += 1
        wd_c[dt.strftime("%a")] += 1
        for lo, hi, tag in HOUR_BINS:
            if lo <= dt.hour < hi:
                bin_c[tag] += 1
                break
        if is_self:
            self_total += 1
        cm = conv_meta.get(cid)
        if cm is None:
            conv_meta[cid] = {"label": m.get("chat_room") or "(未知)", "is_group": bool(m.get("is_group_chat")),
                              "first": m["ts"], "last": m["ts"], "count": 1, "self": 1 if is_self else 0}
        else:
            cm["count"] += 1
            cm["last"] = max(cm["last"], m["ts"])
            if is_self:
                cm["self"] += 1
        if m.get("is_group_chat") and mt == 1:
            sender_in_groups[(m.get("chat_room") or "?", m.get("sender") or "?")] += 1

    t0 = datetime.datetime.fromtimestamp(min(m["ts"] for m in msgs))
    t1 = datetime.datetime.fromtimestamp(max(m["ts"] for m in msgs))
    groups = sum(1 for c in conv_meta.values() if c["is_group"])
    summary = {
        "total_messages": n,
        "time_range": [t0.strftime("%Y-%m-%d %H:%M"), t1.strftime("%Y-%m-%d %H:%M")],
        "n_conversations": len(conv_meta),
        "n_group_conversations": groups,
        "n_direct_conversations": len(conv_meta) - groups,
        "self_message_ratio": round(self_total / n, 4) if n else 0,
        "msg_type_distribution": {str(k): v for k, v in type_c.most_common()},
        "yearly": {str(k): v for k, v in sorted(year_c.items())},
        "hourly": {str(h): hour_c.get(h, 0) for h in range(24)},
        "hour_bins": dict(bin_c),
        "weekday": dict(wd_c),
    }
    rows_conv = [{
        "会话": cm["label"], "类型": "群聊" if cm["is_group"] else "单聊", "消息数": cm["count"],
        "我发出": cm["self"], "我发出占比": round(cm["self"] / cm["count"], 3),
        "最早": datetime.datetime.fromtimestamp(cm["first"]).strftime("%Y-%m-%d"),
        "最近": datetime.datetime.fromtimestamp(cm["last"]).strftime("%Y-%m-%d"),
        "conversation_id": cid,
    } for cid, cm in sorted(conv_meta.items(), key=lambda kv: -kv[1]["count"])[:60]]
    rows_members = [{"群聊": g, "成员": s, "文本消息数": c}
                    for (g, s), c in sender_in_groups.most_common(80)]
    dump_csv(outdir, "会话Top60.csv", rows_conv)
    dump_csv(outdir, "群成员文本Top80.csv", rows_members)
    dump_csv(outdir, "月度趋势.csv", [{"月份": k, "消息数": v} for k, v in sorted(month_c.items())])
    dump_csv(outdir, "小时分布.csv", [{"小时": f"{h:02d}", "消息数": hour_c.get(h, 0)} for h in range(24)])
    dump_csv(outdir, "时段分布.csv", [{"时段": k, "消息数": v} for k, v in bin_c.items()])
    dump_csv(outdir, "星期分布.csv", [{"星期": WD_CN[k], "消息数": wd_c[k]} for k in WD_ORDER])
    dump_csv(outdir, "消息类型.csv", [{"类型ID": k, "类型": TYPE_LABEL.get(int(k), f"其他({k})"), "消息数": v}
                                  for k, v in type_c.most_common()])
    dump_csv(outdir, "年度趋势.csv", [{"年份": k, "消息数": v} for k, v in sorted(year_c.items())])
    return summary


def analyze_group(msgs, label, outdir):
    G = [m for m in msgs if (m.get("chat_room") or "").strip() == label]
    if not G:
        print(f"!! 未找到群: {label}")
        sys.exit(1)
    n = len(G)
    type_c, year_c, month_c, hour_c, wd_c, day_c = (collections.Counter() for _ in range(6))
    sender_c, sender_text_c = collections.Counter(), collections.Counter()
    sender_first, sender_last, self_total = {}, {}, 0
    for m in G:
        dt = datetime.datetime.fromtimestamp(m["ts"])
        type_c[m.get("msg_type")] += 1
        year_c[dt.year] += 1
        month_c[f"{dt.year}-{dt.month:02d}"] += 1
        hour_c[dt.hour] += 1
        wd_c[dt.strftime("%a")] += 1
        day_c[dt.strftime("%Y-%m-%d")] += 1
        s = m.get("sender") or "?"
        sender_c[s] += 1
        sender_first.setdefault(s, m["ts"])
        sender_last[s] = max(sender_last.get(s, 0), m["ts"])
        if m.get("is_self"):
            self_total += 1
        if m.get("msg_type") == 1:
            sender_text_c[s] += 1
    ts_all = [m["ts"] for m in G]
    t0, t1 = datetime.datetime.fromtimestamp(min(ts_all)), datetime.datetime.fromtimestamp(max(ts_all))
    top_day = day_c.most_common(1)[0]
    summary = {
        "群名": label, "总消息": n,
        "时间范围": [t0.strftime("%Y-%m-%d"), t1.strftime("%Y-%m-%d")],
        "覆盖天数": round((max(ts_all) - min(ts_all)) / 86400, 1),
        "有消息的天数": len(day_c),
        "日均消息(有消息日)": round(n / len(day_c), 1) if day_c else 0,
        "参与人数(发言)": len(sender_c),
        "我发出占比": round(self_total / n, 4),
        "文本占比": round(sum(sender_text_c.values()) / n, 4),
        "类型分布": {TYPE_LABEL.get(int(k), f"其他{k}"): v for k, v in type_c.most_common()},
        "年度分布": dict(sorted(year_c.items())),
        "最活跃5天": day_c.most_common(5),
        "最长沉默期TOP3": silence_gaps(day_c),
    }
    dump_csv(outdir, "群_成员发言Top50.csv", [{
        "成员": s, "总消息": c, "文本": sender_text_c.get(s, 0),
        "首次发言": datetime.datetime.fromtimestamp(sender_first[s]).strftime("%Y-%m-%d"),
        "最近发言": datetime.datetime.fromtimestamp(sender_last[s]).strftime("%Y-%m-%d")}
        for s, c in sender_c.most_common(50)])
    dump_csv(outdir, "群_月度.csv", [{"月份": k, "消息数": v} for k, v in sorted(month_c.items())])
    dump_csv(outdir, "群_小时.csv", [{"小时": f"{h:02d}", "消息数": hour_c.get(h, 0)} for h in range(24)])
    dump_csv(outdir, "群_星期.csv", [{"星期": k, "消息数": wd_c[k]} for k in WD_ORDER])
    dump_csv(outdir, "群_类型.csv", [{"类型ID": k, "类型": TYPE_LABEL.get(int(k), f"其他{k}"), "消息数": v}
                                  for k, v in type_c.most_common()])
    dump_csv(outdir, "群_年度.csv", [{"年份": k, "消息数": v} for k, v in sorted(year_c.items())])
    dump_csv(outdir, "群_活跃日Top30.csv", [{"日期": k, "消息数": v} for k, v in day_c.most_common(30)])
    with open(os.path.join(outdir, "群_全部消息.json"), "w", encoding="utf-8") as f:
        json.dump(G, f, ensure_ascii=False)
    return summary, top_day


def main():
    ap = argparse.ArgumentParser(description="微信聊天记录多维分析")
    ap.add_argument("--json", required=True, help="chatlog-keeper 导出的 wechat_messages.json")
    ap.add_argument("--outdir", required=True, help="分析输出目录")
    ap.add_argument("--group", default=None, help="单群深度分析（传群名）")
    args = ap.parse_args()
    os.makedirs(args.outdir, exist_ok=True)

    print(f"[load] {args.json}")
    with open(args.json, encoding="utf-8") as f:
        msgs = json.load(f)
    n = len(msgs)
    print(f"[ok] {n} messages")

    if args.group:
        summary, top_day = analyze_group(msgs, args.group, args.outdir)
        checks = {"群消息数与类型合计一致": sum(summary["类型分布"].values()) == summary["总消息"]}
    else:
        summary = analyze_all(msgs, args.outdir)
        checks = {
            "年度合计=总数": sum(summary["yearly"].values()) == n,
            "小时合计=总数": sum(summary["hourly"].values()) == n,
            "星期合计=总数": sum(summary["weekday"].values()) == n,
        }
    summary["consistency_checks"] = checks
    print("[checks]", checks)
    with open(os.path.join(args.outdir, "summary.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2, default=str)
    print(json.dumps(summary, ensure_ascii=False, indent=1, default=str)[:2000])


if __name__ == "__main__":
    main()
