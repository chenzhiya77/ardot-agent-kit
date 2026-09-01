#!/usr/bin/env python3
"""生成插件分发 ZIP，并按**清单**校验。

为什么是脚本而不是文档：应打包集合有两个相反的翻车方向，靠人记必然出错 ——
  · 照目录遍历打包，会把 gitignore 掉的构建产物（__pycache__ 等）一起打进去；
  · 照 git ls-files 打包，又会把「跟踪但不分发」的 .workbuddy/ 打进去。

期望集合为什么单独存成 package-manifest.txt：早先这脚本拿「同一份 ls-files 过滤结果」
既去铺 staging 又去核对包内成员，于是任何过滤口径写错都会同时改变两边 ——
实测三个红路径全部返回 0，那是自证，不是校验。现在核对只认清单，
改口径必须显式 --write-manifest，错一边就会在另一边炸出来。

Windows 上还必须用 System32 的 tar 出 zip：Git Bash 自带 GNU tar，
即使后缀写成 .zip 也只产出 ustar 归档，解压方会直接报 BadZipFile。

用法:
    python scripts/package.py                     # 打包 + 按清单校验
    python scripts/package.py --write-manifest    # 有意改清单（新增/移除技能文件后）
    python scripts/package.py --out <路径>        # 打到别处，别覆盖正式产物
退出码: 0 = 通过；1 = 中止或校验失败。
"""

import argparse
import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOP = os.path.basename(ROOT)                                  # ZIP 里的顶层目录名
DEFAULT_OUT = os.path.join(ROOT, f"{TOP}.zip")
MANIFEST = os.path.join(ROOT, "scripts", "package-manifest.txt")

# 跟踪、但不随插件分发（WorkBuddy 侧的记忆转储）
NOT_SHIPPED = (".workbuddy/",)
# 任何情况下都不许出现在包里。与上面的 NOT_SHIPPED 分开写，是为了让校验这一侧
# 不完全依赖打包那一侧的同一份配置。
BANNED_PREFIX = (".workbuddy/", "__pycache__/")
BANNED_SUFFIX = (".pyc", ".zip")

SYSTEM_TAR = r"C:\Windows\System32\tar.exe"   # 写绝对路径：走 PATH 会命中 Git 的 GNU tar
EXPECTED_MODE = 0o100666


def fail(msg):
    print(f"✗ {msg}")
    return 1


def git_z(*args):
    """跑 git 并按 NUL 切分 —— 调用方给的参数必须本身带 -z。"""
    r = subprocess.run(["git", "-C", ROOT, *args], capture_output=True)
    if r.returncode != 0:
        raise SystemExit(fail("git " + " ".join(args) + " 失败："
                              + r.stderr.decode("utf-8", "replace").strip()))
    return [s.decode("utf-8").replace("\\", "/") for s in r.stdout.split(b"\x00") if s]


def read_manifest():
    if not os.path.isfile(MANIFEST):
        return None
    with open(MANIFEST, encoding="utf-8") as f:
        return sorted(l.strip() for l in f if l.strip() and not l.startswith("#"))


def banned(name):
    return name.startswith(BANNED_PREFIX) or name.endswith(BANNED_SUFFIX)


def write_manifest(files):
    with open(MANIFEST, "w", encoding="utf-8", newline="\n") as f:
        f.write("# 分发 ZIP 的应打包清单 —— scripts/package.py 用它校验，不读 git 跟踪清单。\n"
                "# 有意增删技能文件后：python scripts/package.py --write-manifest\n")
        f.write("\n".join(sorted(files)) + "\n")
    print(f"✓ 清单已改写：{len(files)} 条")


def update_manifest(new, assume_yes):
    """清单是校验的独立基准，所以改它必须过人手 —— 否则口径写错会悄悄变成新基线。"""
    dirty = [f for f in new if banned(f)]
    if dirty:
        return fail(f"这些路径不该出现在分发包里，拒绝写入清单：{dirty}")

    old = read_manifest() or []
    added = sorted(set(new) - set(old))
    removed = sorted(set(old) - set(new))
    if not added and not removed:
        print("清单与当前应打包集合已一致，无需改写。")
        return 0
    print(f"清单变更（现 {len(old)} → 新 {len(new)}）：+{len(added)} −{len(removed)}")
    for f in added:
        print("   +", f)
    for f in removed:
        print("   −", f)
    if not assume_yes:
        if not sys.stdin.isatty():
            return fail("非交互环境，拒绝自作主张改写清单。核对上面的增删后加 --yes")
        if input("确认改写清单？[y/N] ").strip().lower() != "y":
            print("已取消改写。")
            return 1
    write_manifest(new)
    return 0


def verify(built, expected):
    """expected 只来自清单 —— 不要接打包那侧算出来的集合，否则又变成自证。"""
    with zipfile.ZipFile(built) as z:
        members = [i for i in z.infolist() if not i.filename.endswith("/")]
        rels = [i.filename.split("/", 1)[1] for i in members]

        extra = sorted(set(rels) - set(expected))
        absent = sorted(set(expected) - set(rels))
        if extra:
            return fail(f"多打包 {len(extra)} 个不该分发的文件：{extra}")
        if absent:
            return fail(f"漏打包 {len(absent)} 个应分发的文件：{absent}"
                        f"\n    若是有意移除，跑 --write-manifest 更新清单")

        for name in rels:
            if banned(name):
                return fail(f"包内混进禁止分发的内容：{name}")

        for i in members:
            rel = i.filename.split("/", 1)[1]
            disk = os.path.join(ROOT, rel.replace("/", os.sep))
            if not os.path.isfile(disk):
                return fail(f"包内有清单外的来源：{rel}")
            if hashlib.sha256(z.read(i)).hexdigest() != hashlib.sha256(open(disk, "rb").read()).hexdigest():
                return fail(f"包内内容与磁盘不一致：{rel}")
            if i.external_attr >> 16 != EXPECTED_MODE:
                return fail(f"权限位异常：{rel} 是 {oct(i.external_attr >> 16)}，应为 {oct(EXPECTED_MODE)}")

    print(f"✓ 校验通过：成员 {len(members)} 与清单双向相符，内容与磁盘逐文件一致，权限位统一")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--allow-untracked", action="store_true",
                    help="有未跟踪文件也照样打包（默认直接失败）")
    ap.add_argument("--write-manifest", action="store_true",
                    help="按当前应打包集合改写清单，然后照常打包校验")
    ap.add_argument("--yes", action="store_true",
                    help="配合 --write-manifest 跳过逐条确认")
    ap.add_argument("--out", default=DEFAULT_OUT, help="产物路径（默认仓库根的 ZIP）")
    args = ap.parse_args()

    if os.name != "nt":
        return fail("这个脚本只在 Windows 上打包（依赖 System32 的 bsdtar）。")
    if not os.path.isfile(SYSTEM_TAR):
        return fail(f"找不到 {SYSTEM_TAR} —— 换 tar 实现前请先确认它产出的是真 zip。")

    loose = git_z("ls-files", "--others", "--exclude-standard", "-z")
    if loose:
        msg = (f"{len(loose)} 个未跟踪、也没被 ignore 的文件不会进 ZIP："
               + ", ".join(loose[:6]) + ("…" if len(loose) > 6 else "")
               + "\n    先 git add，或确认该忽略后写进 .gitignore；"
                 "确实要按现状打包就加 --allow-untracked")
        if not args.allow_untracked:
            return fail(msg)
        print(f"提示: {msg}")

    tracked = git_z("ls-files", "-z")
    want = [f for f in tracked if not f.startswith(NOT_SHIPPED)]
    missing = [f for f in want if not os.path.isfile(os.path.join(ROOT, f.replace("/", os.sep)))]
    if missing:
        return fail(f"跟踪清单里有文件不在磁盘上（被删了？先处理干净）：{missing}")

    if args.write_manifest:
        rc = update_manifest(want, args.yes)
        if rc:
            return rc
    expected = read_manifest()
    if expected is None:
        return fail("缺 scripts/package-manifest.txt —— 先跑 --write-manifest 生成基线。")

    stage = tempfile.mkdtemp(prefix="ardot-pack-")
    try:
        for f in want:
            dst = os.path.join(stage, TOP, f.replace("/", os.sep))
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(os.path.join(ROOT, f.replace("/", os.sep)), dst)

        r = subprocess.run([SYSTEM_TAR, "-a", "-c", "-f", "out.zip", TOP],
                           cwd=stage, capture_output=True, text=True)
        if r.returncode != 0:
            return fail("tar 打包失败：" + (r.stderr or r.stdout).strip())
        built = os.path.join(stage, "out.zip")
        if not zipfile.is_zipfile(built):
            return fail("产出的不是合法 zip（tar 实现选错了）。")

        rc = verify(built, expected)
        if rc:
            return rc

        shutil.copy2(built, args.out)
        print(f"✓ {os.path.basename(args.out)}  {os.path.getsize(args.out):,} 字节 / "
              f"{len(expected)} 文件（跟踪 {len(tracked)} − 不分发 {len(tracked) - len(want)}）")
        return 0
    finally:
        shutil.rmtree(stage, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
