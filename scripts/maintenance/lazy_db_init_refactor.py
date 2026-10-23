"""
一次性重构脚本：把各服务的「导入期数据库 I/O」改为「首次使用时惰性初始化」。

处理规则（基于 AST 精确定位，避免误伤）：
1. 从 ``__init__`` 中移除 ``self._init_db()`` / ``self._init_indexes()`` / ``self.load_st_stocks()`` 调用；
2. 给该初始化方法加幂等守卫（``_db_initialized`` 标志）；
3. 仅在**确实访问数据库集合**的公开方法入口插入初始化调用。

用法： python scripts/maintenance/lazy_db_init_refactor.py [--dry-run]
"""

from __future__ import annotations

import argparse
import ast
import sys
from pathlib import Path
from typing import Dict, List, Tuple

ROOT = Path(__file__).resolve().parents[2]

# 文件 -> (类名, 初始化方法名, 表示"访问数据库"的属性名片段)
TARGETS: List[Tuple[str, str, str, Tuple[str, ...]]] = [
    ("app/core/crawler_fund.py", "FundRankingCrawler", "_init_db", ("self.collection",)),
    ("app/core/crawler_popularity.py", "PopularityRankingCrawler", "_init_db", ("self.collection",)),
    ("app/services/crawler_service.py", "CrawlerService", "_init_db", ("self.collection",)),
    (
        "app/services/scrapy_crawler_service.py",
        "ScrapyCrawlerService",
        "_init_indexes",
        ("self.popularity_collection", "self.capital_flow_collection", "self.expert_ranking_collection"),
    ),
    (
        "app/services/advanced_stock_selector_service.py",
        "AdvancedStockSelectorService",
        "_init_db",
        (
            "self.crawler_collection",
            "self.stock_data_collection",
            "self.screening_results_collection",
        ),
    ),
    (
        "app/services/stock_selector_service.py",
        "StockSelectorService",
        "_init_db",
        ("self.crawler_collection", "self.screening_results_collection"),
    ),
    ("app/services/st_filter_service.py", "STFilterService", "load_st_stocks", ("self.st_collection", "self.filter_log_collection", "self.st_stock_names")),
]


def _method_bodies(tree: ast.AST) -> Dict[str, ast.FunctionDef]:
    """收集模块内所有方法（按首次出现顺序）。"""
    result: Dict[str, ast.FunctionDef] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            result.setdefault(node.name, node)
    return result


def _class_methods(cls: ast.ClassDef) -> Dict[str, ast.FunctionDef]:
    """收集**目标类自身**的方法 —— 不能用模块级查找，否则会命中其他类的同名方法。"""
    return {
        node.name: node
        for node in cls.body
        if isinstance(node, ast.FunctionDef)
    }


def _insert_after_docstring(lines: List[str], node: ast.FunctionDef) -> int:
    """返回「函数体第一条语句之前」的 0-based 行号。"""
    start = node.body[0].lineno - 1  # 0-based
    if isinstance(node.body[0], ast.Expr) and isinstance(node.body[0].value, ast.Constant):
        value = node.body[0].value
        if isinstance(value, str):
            # docstring 结束行
            return node.body[0].end_lineno  # 已是 1-based 结束行 -> 0-based 下一行
    return start


def process(rel_path: str, class_name: str, init_method: str, db_attrs: Tuple[str, ...], dry: bool) -> int:
    path = ROOT / rel_path
    source = path.read_text(encoding="utf-8")
    lines = source.splitlines(keepends=True)
    tree = ast.parse(source)

    classes = {n.name: n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)}
    if class_name not in classes:
        print(f"  [跳过] {rel_path}: 未找到类 {class_name}")
        return 0

    cls = classes[class_name]
    methods = _class_methods(cls)

    # --- 1) 找到 __init__ 中对初始化方法的调用，标记删除 ---
    remove_lines: List[int] = []
    init_node = methods.get("__init__")
    if init_node:
        for sub in ast.walk(init_node):
            if (
                isinstance(sub, ast.Expr)
                and isinstance(sub.value, ast.Call)
                and isinstance(sub.value.func, ast.Attribute)
                and sub.value.func.attr == init_method
                and isinstance(sub.value.func.value, ast.Name)
                and sub.value.func.value.id == "self"
            ):
                remove_lines.append(sub.lineno - 1)

    # --- 2) 找到真正访问数据库集合的公开方法 ---
    target_methods: List[ast.FunctionDef] = []
    for node in cls.body:
        if not isinstance(node, ast.FunctionDef):
            continue
        if node.name.startswith("_") and not node.name.startswith("__"):
            continue
        if node.name in ("__init__", init_method):
            continue
        seg = ast.get_source_segment(source, node) or ""
        if any(attr in seg for attr in db_attrs):
            target_methods.append(node)

    # --- 3) 给初始化方法加幂等守卫 ---
    guard_at: List[int] = []
    guard_text: List[str] = []
    init_node = methods.get(init_method)
    if init_node and init_node.name in methods:
        seg = ast.get_source_segment(source, init_node) or ""
        if "_db_initialized" not in seg:
            has_doc = (
                isinstance(init_node.body[0], ast.Expr)
                and isinstance(init_node.body[0].value, ast.Constant)
                and isinstance(init_node.body[0].value.value, str)
            )
            if has_doc:
                # edits[idx] 的语义是「插在 1-based 第 idx+1 行之后」，
                # 因此 docstring 结束行(1-based)要减 1 才能紧跟在 docstring 后面。
                guard_at.append(init_node.body[0].end_lineno - 1)
            else:
                guard_at.append(init_node.body[0].lineno - 1)
            guard_text = [
                "        # 惰性初始化守卫：只在首次访问数据库时执行一次\n",
                "        if getattr(self, \"_db_initialized\", False):\n",
                "            return\n",
                "        self._db_initialized = True\n",
            ]

    # --- 4) 组装新文件内容 ---
    inserts: Dict[int, List[str]] = {}
    for node in target_methods:
        at = _insert_after_docstring(lines, node)
        inserts.setdefault(at, []).append(f"        self.{init_method}()\n")

    edits: Dict[int, List[str]] = {}
    for at, texts in inserts.items():
        edits.setdefault(at, []).extend(texts)
    for at in guard_at:
        edits.setdefault(at, []).extend(guard_text)

    # 在目标类的 __init__ 中声明状态字段（定位到该类的 __init__，而非文件首个）
    class_init = None
    for node in cls.body:
        if isinstance(node, ast.FunctionDef) and node.name == "__init__":
            class_init = node
            break
    state_insert_at = (class_init.body[0].lineno - 1) if class_init else None

    out: List[str] = []
    for idx, line in enumerate(lines):
        if idx in remove_lines:
            continue  # 删除对初始化方法的导入期调用
        out.append(line)
        for text in edits.get(idx, []):
            out.append(text)
        if state_insert_at is not None and idx == state_insert_at:
            out.append("        # 数据库初始化推迟到首次使用（避免模块导入阶段的网络 I/O）\n")
            out.append("        self._db_initialized = False\n")

    new_source = "".join(out)

    if not dry:
        path.write_text(new_source, encoding="utf-8")

    print(
        f"  [OK] {rel_path}: 移除 {len(remove_lines)} 处导入期调用, "
        f"注入 {len(target_methods)} 个方法入口, 守卫 {'已加' if guard_at else '已存在'}"
    )
    return len(target_methods)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    print("惰性数据库初始化重构：")
    total = 0
    for rel_path, class_name, init_method, db_attrs in TARGETS:
        total += process(rel_path, class_name, init_method, db_attrs, args.dry_run)
    print(f"\n共处理 {total} 个方法入口")
    return 0


if __name__ == "__main__":
    sys.exit(main())
