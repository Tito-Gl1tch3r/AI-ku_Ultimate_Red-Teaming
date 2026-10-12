#!/usr/bin/env python3
"""通用微信 4.1.x Windows 数据库密钥恢复驱动（跨设备 / 跨微信版本通用）

流程（对应 WeChatDataAnalysis/LifeArchiveProject 方案）:
  Step 1  scan.py     静态提取 XOR key（特征随微信版本变化 -> 每次运行自动重提）
  Step 2  key_v4.py   只读扫描运行中微信进程内存，恢复登录账号的 passphrase
  Step 3  recover_key 内置 HMAC 校验（拿 db 文件 page1 验证候选 key 真伪）

用法:
  python run_recovery_generic.py <PID> <Weixin.dll路径> <db_storage目录> [更多db_storage目录...]

示例:
  python run_recovery_generic.py <PID> \
      "D:/Program Files (x86)/Weixin/<版本号>/Weixin.dll" \
      "C:/Users/<用户名>/Documents/xwechat_files/wxid_xxx_abcd/db_storage"

前提:
  - 目标微信账号必须【已登录】且微信正在运行（passphrase 只存在于登录态内存）
  - PID = 主进程(窗口标题为「微信」的 Weixin.exe)，勿取子进程
  - 依赖: pip install pefile pycryptodome pymem yara-python

产物（写入本脚本同目录）:
  recovered_key.txt
    pid      = 目标进程 PID
    db       = 首个校验通过的 db 文件
    xor_key  = 用到的静态 XOR key
    raw      = 内存扫到的 32B 原始值
    final    = raw XOR xor_key = **passphrase**（后续解密数据库真正使用的密钥，64 位 hex）

退出码: 0=成功 1=未命中/失败 2=参数错误

方案门控（勿与 chatlog-keeper extract-key 混淆）:
  - 本脚本 = WeChatDataAnalysis 实现（scan.py 静态 XOR + key_v4.py 内存扫描 + HMAC 校验），
    微信 4.1.13.12 实测通过（登录 wxid 小号 19/19 库 HMAC 校验通过 + 导出 197 条）。
  - chatlog-keeper 自带 extract-key --method passive：微信 >=4.1.10.31 官方声明+实测失败，勿用。
  - chatlog-keeper extract-key --method active / 源码包 windows_wechat_get_key.ps1
    （调试器 attach）：反调试 + 封号风险，已评估不可行，勿用。
  - 正确链路：本脚本恢复出 final(passphrase) -> chatlog-keeper set-key --key-stdin 注入
    -> chatlog-keeper wechat --account <账号> 导出。

0/N 命中最常见原因（先查再重跑）:
  1. 目标账号未登录（切换账号后 PID 会变，需重新取 PID）
  2. PID 取成了子进程（应为窗口标题为「微信」的主进程 Weixin.exe）
  3. db_storage 指向了未登录的账号目录（多账号时最易错）
  4. 权限不足（尝试以管理员运行）
  排除上述后仍失败才考虑微信版本特征变化（需更新 scan.py 的 YARA 特征码）。
"""
import sys, os, time, glob, json

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import scan     # WeChatDataAnalysis: 静态 XOR key 提取
import key_v4   # WeChatDataAnalysis: 内存扫描 + PBKDF2/HMAC 校验


def parse_args():
    args = sys.argv[1:]
    if len(args) < 3:
        print(__doc__)
        sys.exit(2)
    pid = int(args[0])
    dll = args[1]
    roots = args[2:]
    if not os.path.isfile(dll):
        print(f"[-] 找不到 Weixin.dll: {dll}")
        sys.exit(2)
    for r in roots:
        if not os.path.isdir(r):
            print(f"[-] 找不到 db_storage 目录: {r}")
            sys.exit(2)
    return pid, dll, roots


def extract_xorkeys(dll):
    """Step1: 静态提取 XOR key 候选（scan.py 结果落到 keys/<version>.jsonl）"""
    # 从路径推断版本号，例如 .../Weixin/4.1.13.12/Weixin.dll -> 4.1.13.12
    norm = dll.replace("\\", "/")
    version = "unknown"
    parts = norm.split("/")
    for i, p in enumerate(parts):
        if p.lower() == "weixin" and i + 1 < len(parts):
            version = parts[i + 1]
            break
    keys_dir = os.path.join(HERE, "keys")
    os.makedirs(keys_dir, exist_ok=True)
    out_jsonl = os.path.join(keys_dir, f"{version}.jsonl")
    if os.path.exists(out_jsonl):
        os.remove(out_jsonl)

    print(f"[*] Step1 静态扫描 {dll}")
    scan.extract_xor_keys_multiprocess(dll, version=version)

    xorkeys = []
    if os.path.exists(out_jsonl):
        for line in open(out_jsonl, encoding="utf-8"):
            try:
                obj = json.loads(line)
                k = obj["key"].replace(" ", "").upper()
                if len(k) == 64:
                    xorkeys.append(k)
            except Exception:
                pass
    xorkeys = list(dict.fromkeys(xorkeys))
    print(f"[*] 提取到 {len(xorkeys)} 枚 XOR key 候选: "
          f"{[k[:12] + '...' for k in xorkeys]}")
    if not xorkeys:
        print("[-] 未提取到 XOR key —— 微信版本特征可能已变化，需更新 scan.py 特征码")
        sys.exit(1)
    return xorkeys


def collect_dbs(roots):
    """每账号目录取一个 >=4096B 的 db 用于 HMAC 校验（同账号各库共用同一 passphrase）"""
    dbs = []
    for root in roots:
        found = None
        for pat in ("contact/contact.db", "message/*.db", "*.db", "*/*.db"):
            for h in sorted(glob.glob(os.path.join(root, pat))):
                if h.endswith(("-wal", "-shm")):
                    continue
                if os.path.isfile(h) and os.path.getsize(h) >= key_v4.PAGE_SIZE:
                    found = h
                    break
            if found:
                break
        if found:
            dbs.append(found)
        else:
            print(f"[!] 账号目录下未找到可用 db: {root}")
    print(f"[*] 用于校验的 db 候选 {len(dbs)} 个:")
    for d in dbs:
        print(f"    {d} ({os.path.getsize(d) // 1024}KB)")
    return dbs


def main():
    t0 = time.time()
    pid, dll, roots = parse_args()
    xorkeys = extract_xorkeys(dll)
    dbs = collect_dbs(roots)
    if not dbs:
        print("[-] 无可用 db 校验，退出")
        sys.exit(1)

    for db in dbs:
        for xk in xorkeys:
            tag = f"db={os.path.basename(os.path.dirname(db))}/{os.path.basename(db)} xor={xk[:12]}..."
            print(f"\n{'=' * 60}\n[*] 尝试 {tag}\n{'=' * 60}")
            key_v4.finish_flag = False  # is_ok 全局标志，逐轮重置
            try:
                raw = key_v4.recover_key(pid, db, bytes.fromhex(xk))
            except Exception as e:
                print(f"[-] recover_key 异常: {e}")
                continue
            if raw:
                final = key_v4.xor_raw_key(bytes.fromhex(raw), bytes.fromhex(xk)).hex()
                print(f"\n[✓] 命中! raw  = {raw}")
                print(f"[✓] final = {final}  (passphrase, 解密用密钥)")
                out = os.path.join(HERE, "recovered_key.txt")
                with open(out, "w") as f:
                    f.write(f"pid={pid}\ndb={db}\nxor_key={xk}\nraw={raw}\nfinal={final}\n")
                print(f"[✓] 已保存到 {out}")
                print(f"[*] 总耗时 {time.time() - t0:.1f}s")
                sys.exit(0)
            print(f"[-] 该组合未命中 (累计 {time.time() - t0:.1f}s)")

    print(f"\n[✗] 全部组合未命中 ({time.time() - t0:.1f}s)")
    print("    可能原因: ①目标账号未登录(切换账号后 PID 变化，请重新取 PID)；"
          "②微信版本特征变化；③权限不足(尝试以管理员运行)")
    sys.exit(1)


if __name__ == "__main__":
    main()
