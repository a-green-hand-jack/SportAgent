#!/usr/bin/env python3
"""PreToolUse 硬约束 hook（地板层）。

拦截真正危险的 Bash 命令、对受保护路径的写入、以及推向受保护分支的 push。
这是 doctrine 的机器强制层，也是**不可调的地板**：即使 human 授权自主窗口或开 bypass
让 permission 层放开，本 hook 仍拦截红线（提权、管道远程执行、递归删数据/产物/.git、
写产物 bytes、push main）。permission 是可调的第一道门，本 hook 是最后一道。

设计要点：用 shlex 做**真正的命令解析**（不是子串正则），因此
- 引号里的字面量（commit message、echo "..."）不会被误当成命令拦（消除误伤）；
- 引号里的真实路径/分支（rm -rf "lab/data"、git push origin "main"）仍能识别（不漏）。
本 hook 是"防误操作"护栏，非对抗性沙箱：不为"把危险命令藏进 python -c / 命令替换"负责
（这类代码执行本就被 allow 的 pytest/uv run 信任，数据安全最终靠 gitignore + 备份）。

协议：Claude Code / Codex 通过 stdin 传 JSON（tool_name / tool_input）；exit 2 = 阻止，
exit 0 = 放行。解析失败保守放行。无第三方依赖。push 到受保护分支需
`CLAUDE_ALLOW_PUSH_MAIN=1` 或 `CODEX_ALLOW_PUSH_MAIN=1`（见 `.agent/autonomous-window.md`）。
"""
import json
import os
import re
import shlex
import subprocess
import sys
from pathlib import Path

# 本脚本自己的仓库根：`_current_branch()` 的 subprocess 调用要锚定到这里，
# 不能依赖调用进程当下的 cwd（cwd 若已漂移进嵌套仓库，会静默检查错误仓库的
# 分支，进而影响 push-to-main 保护逻辑的判断）。本文件在 `.claude/hooks/` 下。
REPO_ROOT = Path(__file__).resolve().parent.parent.parent

# 受保护 bytes / 私有 / 追踪产物路径。
PROTECTED_PREFIXES = (
    "lab/data/", "lab/runs/", "lab/models/", "lab/infra/private/",
    "checkpoints/", "wandb/", "mlruns/",
)
PROTECTED_DIRS = tuple(p.rstrip("/") for p in PROTECTED_PREFIXES)
PROTECTED_FILES = (".env",)

# 受保护分支：push 需 human 明确放行。
PROTECTED_BRANCHES = {"main", "master"}
PUSH_ESCAPE_ENVS = ("CLAUDE_ALLOW_PUSH_MAIN", "CODEX_ALLOW_PUSH_MAIN")

# rm -r 允许递归删除的安全目标（缓存/构建/临时，可再生）。
SAFE_RM_BASENAMES = {
    "__pycache__", ".pytest_cache", ".ruff_cache", ".mypy_cache",
    ".ipynb_checkpoints", ".coverage", "htmlcov", ".tox",
    "dist", "build", ".cache",
}

# curl|sh / wget|sh：命令边界处的 curl/wget 管道到 shell（在原始串上匹配，边界锚定避免误伤）。
CURL_PIPE_SH = re.compile(
    r"(?:^|[;&|]|\n)\s*(?:\w+=\S+\s+)*(?:curl|wget)\b[^;&|\n]*\|\s*(?:sudo\s+)?(?:sh|bash|zsh)\b"
)

# 兜底：同一命令段内 rm/shred 触碰受保护 bytes（覆盖 find -exec 等嵌套；在去引号串上匹配）。
DESTRUCTIVE_PROTECTED = re.compile(
    r"\b(?:rm|shred|srm|truncate|unlink)\b[^;|&\n]*"
    r"\b(?:lab/(?:data|runs|models)|checkpoints|wandb|lab/infra/private)\b"
)


def _norm(path: str) -> str:
    p = path.strip().strip('"').strip("'")
    if p.startswith("./"):
        p = p[2:]
    return p


def _is_protected_file(path: str) -> bool:
    p = _norm(path)
    if p in PROTECTED_FILES:
        return True
    return any(p.startswith(prefix) for prefix in PROTECTED_PREFIXES)


def _touches_protected_dir(path: str) -> bool:
    p = _norm(path).rstrip("/")
    if p in PROTECTED_FILES:
        return True
    return any(p == d or p.startswith(d + "/") for d in PROTECTED_DIRS)


def _dequote(cmd: str) -> str:
    """去掉单/双引号内的字面量（用于兜底子串检查），避免 echo/commit message 误伤。"""
    cmd = re.sub(r"'[^']*'", " ", cmd)
    cmd = re.sub(r'"[^"]*"', " ", cmd)
    return cmd


def _current_branch() -> str:
    try:
        out = subprocess.run(
            ["git", "branch", "--show-current"],
            capture_output=True, text=True, timeout=5,
            cwd=str(REPO_ROOT),
        )
        return out.stdout.strip()
    except Exception:  # noqa: BLE001  无 git / 超时 / 非仓库
        return ""


def _commands(raw_cmd: str) -> list[list[str]]:
    """把一条 bash 串解析成若干简单命令的 token 列表（引号已解，按 ; | & < > 分段）。
    解析失败时回退到空白分割（保守）。"""
    try:
        lex = shlex.shlex(raw_cmd, posix=True, punctuation_chars=True)
        lex.whitespace_split = True
        toks = list(lex)
    except ValueError:
        toks = raw_cmd.split()
    cmds: list[list[str]] = []
    cur: list[str] = []
    for t in toks:
        if t and set(t) <= set(";|&<>()"):  # 运算符/分隔符 token
            if cur:
                cmds.append(cur)
                cur = []
        else:
            cur.append(t)
    if cur:
        cmds.append(cur)
    return cmds


def _split_env(tokens: list[str]) -> tuple[list[str], list[str]]:
    """拆出前导 env 赋值，返回 (env_assignments, rest)。"""
    i = 0
    while i < len(tokens) and re.match(r"^[A-Za-z_]\w*=", tokens[i]):
        i += 1
    return tokens[:i], tokens[i:]


def _rm_target_dangerous(t: str) -> bool:
    p = t.strip()
    if not p:
        return False
    if p in ("/", ".", "./", "..", "~", "*", "./*", "/*"):
        return True
    if p.startswith(("~", "$")):
        return True
    if p.startswith("/") and not p.startswith("/tmp/"):
        return True  # 绝对路径（除 /tmp）
    parts = _norm(p).split("/")
    if ".." in parts or ".git" in parts:
        return True
    if p.startswith("*"):
        return True
    if _touches_protected_dir(p):
        return True
    return False


def _rm_reason(args: list[str]) -> str | None:
    recursive = any(
        a in ("-r", "-R", "--recursive")
        or (a.startswith("-") and not a.startswith("--") and re.search(r"[rR]", a))
        for a in args
    )
    if not recursive:
        return None
    targets = [a for a in args if not a.startswith("-")]
    for t in targets:
        base = os.path.basename(_norm(t).rstrip("/"))
        if base in SAFE_RM_BASENAMES and not _rm_target_dangerous(t):
            continue
        if _rm_target_dangerous(t):
            return (
                f"rm -r 触碰高风险目标：{t}。数据/产物/checkpoint、.git、绝对路径(非 /tmp)、"
                "~、仓库根、.. 禁止递归删除；缓存/构建/临时目录可删。"
            )
    return None


def _mvcp_reason(name: str, args: list[str]) -> str | None:
    for a in args:
        if a.startswith("-"):
            continue
        if _touches_protected_dir(a):
            return f"{name} 触碰受保护数据/产物路径：{a}。移动/覆盖/删除 bytes 走 human gate。"
    return None


def _git_push_protected(push_args: list[str]) -> bool:
    refs = [a for a in push_args if not a.startswith("-")]
    for a in refs:
        for part in re.split(r"[:/]", a):
            if part in PROTECTED_BRANCHES:
                return True
    if len(refs) <= 1:  # 裸 push（无显式 refspec）→ 看当前分支
        return _current_branch() in PROTECTED_BRANCHES
    return False


def _patch_paths(patch_text: str) -> list[str]:
    paths: list[str] = []
    for line in patch_text.splitlines():
        for prefix in (
            "*** Add File: ",
            "*** Update File: ",
            "*** Delete File: ",
            "*** Move to: ",
        ):
            if line.startswith(prefix):
                paths.append(line[len(prefix) :].strip())
                break
    return paths


def _block(reason: str) -> None:
    out = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }
    print(json.dumps(out))
    print(f"[pre_tool_guard] 阻止：{reason}", file=sys.stderr)
    sys.exit(2)


def _check_bash(raw_cmd: str) -> None:
    # curl|sh / wget|sh 在原始串上边界锚定检查（分词会拆散管道，故单独处理）。
    if CURL_PIPE_SH.search(raw_cmd):
        _block("curl/wget | sh 远程执行禁止")

    # 兜底：嵌套（find -exec 等）删受保护 bytes。去引号避免误伤字符串字面量。
    if DESTRUCTIVE_PROTECTED.search(_dequote(raw_cmd)):
        _block("破坏性命令触碰受保护数据/产物路径（含 find -exec 等嵌套）。删/移 bytes 走 human gate。")

    session_escape = any(
        os.environ.get(env, "").strip().lower() in ("1", "true", "yes")
        for env in PUSH_ESCAPE_ENVS
    )

    for tokens in _commands(raw_cmd):
        envs, rest = _split_env(tokens)
        if not rest:
            continue
        name = os.path.basename(rest[0])
        args = rest[1:]
        cmd_escape = session_escape or any(
            re.match(rf"^{env}=(1|true|yes)$", e, re.IGNORECASE)
            for env in PUSH_ESCAPE_ENVS
            for e in envs
        )

        if name == "sudo":
            _block("sudo 提权禁止")
        if name in ("pip", "pip3") and args[:1] == ["install"]:
            _block("pip install 禁止：用 uv add（见 CLAUDE.md）")
        if name in ("python", "python3") and args[:2] == ["-m", "pip"] and "install" in args:
            _block("python -m pip install 禁止：用 uv add")
        if name == "rm":
            reason = _rm_reason(args)
            if reason:
                _block(reason)
        if name in ("mv", "cp", "rsync", "dd"):
            reason = _mvcp_reason(name, args)
            if reason:
                _block(reason)
        if name == "git" and args[:1] == ["push"]:
            if _git_push_protected(args[1:]) and not cmd_escape:
                _block(
                    f"push 到受保护分支（{'/'.join(sorted(PROTECTED_BRANCHES))}）需 human 明确放行："
                    "命令前加 `CLAUDE_ALLOW_PUSH_MAIN=1 ` / `CODEX_ALLOW_PUSH_MAIN=1 ` "
                    "或 session 内 export。topic/实验分支不受限。"
                )


def main() -> None:
    raw = sys.stdin.read()
    if not raw.strip():
        sys.exit(0)
    try:
        event = json.loads(raw)
    except json.JSONDecodeError:
        sys.exit(0)  # 保守放行

    tool = event.get("tool_name", "")
    tool_input = event.get("tool_input", {}) or {}

    if tool == "Bash":
        _check_bash(tool_input.get("command", "") or "")
    elif tool in ("Edit", "Write", "NotebookEdit"):
        path = tool_input.get("file_path") or tool_input.get("notebook_path") or ""
        if path and _is_protected_file(path):
            _block(
                f"受保护路径不可写：{path}。bytes/私有/产物只留 index，删改走 human gate。"
            )
    elif tool == "apply_patch":
        patch_text = tool_input.get("command", "") or ""
        for path in _patch_paths(patch_text):
            if _is_protected_file(path):
                _block(
                    f"受保护路径不可写：{path}。bytes/私有/产物只留 index，删改走 human gate。"
                )

    sys.exit(0)


if __name__ == "__main__":
    main()
