#!/usr/bin/env python3
"""全账号 HMAC 校验：用 passphrase(hex, 64位) 验证某账号 db_storage 下所有 >=4KB 库文件。
用法:
    python verify_account.py <passphrase_hex> [db_root]
默认 db_root = 自动探测 ~/Documents/xwechat_files 下第一个含 db_storage 的账号
说明: 复用 key_v4.is_ok 的原始算法路径，但每文件重置全局 finish_flag；
      passphrase 须为 XOR 变换后的最终 passphrase（internal_db_key 传 None）。
"""
import sys, os, glob, io, contextlib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import key_v4


def find_default_root():
    """自动探测微信数据目录下第一个账号的 db_storage（跨设备，无本机路径硬编码）。"""
    docs = os.path.join(os.path.expanduser("~"), "Documents", "xwechat_files")
    if os.path.isdir(docs):
        for name in sorted(os.listdir(docs)):
            cand = os.path.join(docs, name, "db_storage")
            if os.path.isdir(cand):
                return cand
    return None


DEFAULT_ROOT = find_default_root()


def collect_dbs(root):
    dbs = []
    for pat in ("*.db", "*/*.db", "*/*/*.db"):
        for h in glob.glob(os.path.join(root, pat)):
            if h.endswith(("-wal", "-shm")):
                continue
            if not os.path.isfile(h):
                continue
            if os.path.getsize(h) >= key_v4.PAGE_SIZE and h not in dbs:
                dbs.append(h)
    return sorted(dbs)


def main():
    if len(sys.argv) < 2:
        print("用法: verify_account.py <passphrase_hex> [db_root]")
        return 2
    pass_hex = sys.argv[1].strip().lower()
    root = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_ROOT
    if root is None:
        print("[-] 未找到 ~/Documents/xwechat_files 下的账号目录，请显式传入 db_root 参数")
        return 2
    try:
        passphrase = bytes.fromhex(pass_hex)
    except ValueError:
        print("[-] passphrase 须为 64 位 hex")
        return 2
    if len(passphrase) != 32:
        print(f"[-] passphrase 长度须 32 字节, got {len(passphrase)}")
        return 2

    dbs = collect_dbs(root)
    print(f"[*] 校验 {os.path.basename(root.rstrip('/\\\\'))} 共 {len(dbs)} 个库 (passphrase {pass_hex[:12]}...)")
    ok = 0
    for db in dbs:
        with open(db, "rb") as f:
            buf = f.read(key_v4.PAGE_SIZE)
        key_v4.finish_flag = False
        with contextlib.redirect_stdout(io.StringIO()):
            good = key_v4.is_ok(passphrase, buf, None)
        tag = os.path.relpath(db, root).replace("\\", "/")
        print(f"    [{'OK' if good else 'XX'}] {tag}")
        if good:
            ok += 1
    print(f"\n[=] 结果: {ok}/{len(dbs)} 通过")
    return 0 if ok == len(dbs) else 1


if __name__ == "__main__":
    sys.exit(main())
