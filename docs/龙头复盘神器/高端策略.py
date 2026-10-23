# -*- coding: utf-8 -*-
"""高端策略 - 龙头复盘神器 Python 美化版(仅高端策略界面)

与原版 v3.4【高端策略】一致的数据与口径:
  · 题材轮动策略 / 飞云主板策略 / 飞云创业板策略 三块列表
  · 列: 日期 | 代码 | 名称 | 当日收盘价 | 次日最高价 | 次日收盘价
  · 每块独立 当前时间数据：YYYYMM + 上月 / 下月 (无数据提示)
  · 当前合计: 当月 次日最高价涨幅 / 次日收盘价涨幅 累计(列对齐, 红涨绿跌)
  · 右侧: 策略方法说明(原二维码改为网址链接, 文字两端对齐)
  · 窗体缩放时: 字体 / 行高 / 列宽 / 排版同步缩放
数据接口(与原版一致):
  https://gp.domekj.top/peizhi/{tcld|zb|cyb}_YYYYMM.txt  (NDJSON)
用法:  pip install requests ttkbootstrap  &&  python 高端策略.py
"""
import datetime as dt
import json
import os
import queue
import threading
import tkinter as tk
import tkinter.font as tkfont
from tkinter import ttk

import requests
import ttkbootstrap as tb

BASE = "https://gp.domekj.top/peizhi/{}{{:06d}}.txt"
WATCH_FILE = "龙头复盘神器_自选列表数据.txt"

STRATEGIES = [
    ("✧ 题材轮动策略", "tcld_", "primary"),
    ("◈ 飞云主板策略", "zb_", "success"),
    ("◈ 飞云创业板策略", "cyb_", "warning"),
]

COLS = ("d", "c", "n", "p", "h", "e")
HEADS = ("日期", "代码", "名称", "当日收盘价", "次日最高价", "次日收盘价")
WIDTHS = (98, 76, 100, 94, 118, 118)
SUM_WIDTHS = sum(WIDTHS)

UP = "#e2484a"
DOWN = "#1aa15c"

# 设计基准尺寸: 窗口为此尺寸时缩放因子=1.0
DESIGN_W, DESIGN_H = 1600, 1000

# 具名字体(统一缩放, 修改一次即全局生效)
BASE_SIZE = {"main": 10, "head": 10, "title": 17, "icon": 19,
             "mono": 9, "foot": 11}
NAMED = {}


def init_fonts():
    """需在根窗口创建后调用"""
    if NAMED:
        return
    NAMED["main"] = tkfont.Font(name="AppMain", family="微软雅黑", size=BASE_SIZE["main"])
    NAMED["head"] = tkfont.Font(name="AppHead", family="微软雅黑", size=BASE_SIZE["head"],
                                weight="bold")
    NAMED["title"] = tkfont.Font(name="AppTitle", family="微软雅黑", size=BASE_SIZE["title"],
                                 weight="bold")
    NAMED["icon"] = tkfont.Font(name="AppIcon", family="Segoe UI Symbol", size=BASE_SIZE["icon"])
    NAMED["mono"] = tkfont.Font(name="AppMono", family="Consolas", size=BASE_SIZE["mono"])
    NAMED["foot"] = tkfont.Font(name="AppFoot", family="微软雅黑", size=BASE_SIZE["foot"],
                                weight="bold")

DESC_TITLE = "✱ " + "微信扫一扫关注微信公众号，了解策略"
QR_URL = "http://weixin.qq.com/r/mp/vRPp8f7EF6NorbqS90av"
DESC_TEXT = (
    "本策略的核心构建逻辑基于多维度专业体系。以多因子权重模型为基础框架，整合量价背离算法、"
    "动态波动率过滤模块与板块资金流向追踪系统，同时嵌入尾盘量能突变捕捉函数，"
    "对当日行情数据进行实时校准。\n"
    "本策略确保信号输出具备稳定性与辨识度，最终在每个交易日14:55左右输出的信号。\n"
    "郑重声明：以下展示的个股信号，仅为当日策略系统输出结果，“不构成任何投资建议或交易引导”。"
    "任何策略均无法适用于所有行情阶段，其成功率受市场环境、使用者对本策略逻辑的理解程度、"
    "实际操作纪律及心态等多重因素影响。信号分享仅用于风格适配性参考与准确性核对，"
    "投资者据此操作需自行承担全部风险。")


# ------------------------------------------------------------------ 数据
def fetch_month(prefix, ym):
    """拉取某策略某月数据; 404 抛 FileNotFoundError"""
    url = BASE.format(prefix).format(ym)
    r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
    if r.status_code == 404:
        raise FileNotFoundError(url)
    r.raise_for_status()
    r.encoding = "utf-8"
    rows = []
    for line in r.text.splitlines():
        line = line.strip()
        if line:
            try:
                rows.append(json.loads(line))
            except ValueError:
                pass
    return rows


def parse_pct(s):
    """'6.76[-0.88%]' -> -0.88 ; 无数据返回 None"""
    if not s or "[" not in s:
        return None
    try:
        return float(s[s.index("[") + 1:].rstrip("%]"))
    except ValueError:
        return None


def pill_text(v):
    return "" if v is None else ("+%.2f%%" % v if v >= 0 else "%.2f%%" % v)


# ------------------------------------------------------------------ 策略卡片
class StrategyPanel(tb.Frame):
    """单个策略卡片: 标题 + 月份切换 + 列表 + 卡片底部当前合计(列对齐)"""

    def __init__(self, master, title, prefix, theme, app):
        super().__init__(master, padding=0)
        self.prefix = prefix
        self.app = app
        self.theme = theme
        self.scale = 1.0
        today = dt.date.today()
        self.ym = today.year * 100 + today.month
        self.default_ym = self.ym

        self.configure(bootstyle="default")
        card = tb.Labelframe(self, text="  %s  " % title, bootstyle=theme, padding=(6, 5))
        card.pack(fill="both", expand=True)
        card.columnconfigure(0, weight=1)
        card.rowconfigure(1, weight=1)
        self.card = card

        # 头部
        head = tb.Frame(card)
        head.grid(row=0, column=0, sticky="ew", pady=(0, 5))
        head.columnconfigure(1, weight=1)
        tb.Button(head, text="◀ 上月", bootstyle="%s-outline" % theme, width=8,
                  command=lambda: self.shift(-1)).grid(row=0, column=0, padx=(0, 6))
        self.chip = tb.Label(head, text="当前时间数据：%d" % self.ym,
                             bootstyle="%s-inverse" % theme, padding=(10, 5),
                             font="AppHead", anchor="center")
        self.chip.grid(row=0, column=1, sticky="ew")
        tb.Button(head, text="下月 ▶", bootstyle="%s-outline" % theme, width=8,
                  command=lambda: self.shift(1)).grid(row=0, column=2, padx=(6, 0))

        # 表格(行列均可伸展, 保证上下左右完整)
        wrap = tb.Frame(card)
        wrap.grid(row=1, column=0, sticky="nsew")
        wrap.columnconfigure(0, weight=1, minsize=120)
        wrap.rowconfigure(0, weight=1, minsize=60)
        self.tree = tb.Treeview(wrap, columns=COLS, show="headings",
                                bootstyle=theme, height=14)
        for c, w, h in zip(COLS, self._col_widths(), HEADS):
            self.tree.heading(c, text=h, anchor="center")
            self.tree.column(c, width=w, minwidth=int(w * 0.9), anchor="center",
                             stretch=True)
        vs = tb.Scrollbar(wrap, orient="vertical", command=self.tree.yview,
                          bootstyle="round-%s" % theme)
        hs = tb.Scrollbar(wrap, orient="horizontal", command=self.tree.xview,
                          bootstyle="round-%s" % theme)
        self.tree.configure(yscrollcommand=vs.set, xscrollcommand=hs.set)
        vs.grid(row=0, column=1, sticky="ns")
        hs.grid(row=1, column=0, sticky="ew")
        self.tree.grid(row=0, column=0, sticky="nsew")
        self.tree.tag_configure("up", foreground=UP)
        self.tree.tag_configure("down", foreground=DOWN)
        self.tree.tag_configure("odd", background="#fbfbfd")
        self.tree.bind("<Button-3>", self._menu)

        # 卡片底部: 当前合计(按表格实际列位置对齐)
        tb.Separator(card).grid(row=2, column=0, sticky="ew")
        foot = tb.Frame(card, padding=0)
        foot.grid(row=3, column=0, sticky="ew", pady=(4, 0))
        foot.grid_propagate(False)
        foot.configure(height=34)
        self.foot_h = 34
        self.foot = foot
        self.f_title = tb.Label(foot, text="当前合计", font="AppFoot", anchor="w")
        self.f_h = tb.Label(foot, text="", font="AppFoot", anchor="center")
        self.f_e = tb.Label(foot, text="", font="AppFoot", anchor="center")
        self.bind("<Configure>", lambda e: self._layout_foot())
        self.load()

    # ------------------------------------------------------------ 数据
    def load(self):
        self.chip.config(text="当前时间数据：%d  ⟳ 加载中" % self.ym)
        ym = self.ym
        self.app.bg(lambda: fetch_month(self.prefix, ym),
                    lambda rows: self._fill(rows, ym))

    def shift(self, n):
        y, m = divmod(self.ym, 100)
        m += n
        if m == 0:
            y, m = y - 1, 12
        elif m == 13:
            y, m = y + 1, 1
        self.ym = y * 100 + m
        self.load()

    def _fill(self, rows, ym):
        self.tree.delete(*self.tree.get_children())
        if rows is None:
            msg = "∅ 上个月无数据！" if ym < self.default_ym else "∅ 下个月无数据！"
            self.tree.insert("", "end", values=(msg, "", "", "", "", ""))
            self.chip.config(text="当前时间数据：%d  ∅" % self.ym)
            self._set_sum(None, None)
            return
        sum_h = sum_e = 0.0
        for i, it in enumerate(rows):
            hi = it.get("highest_price", "")
            close = it.get("closing_price", "")
            ph, pe = parse_pct(hi), parse_pct(close)
            if ph is not None:
                sum_h += ph
            if pe is not None:
                sum_e += pe
            tags = ("odd",) if i % 2 else ()
            if ph is not None:
                tags += ("up",) if ph >= 0 else ("down",)
            vals = (it.get("selected_date", ""), it.get("code", ""), it.get("name", ""),
                    "" if it.get("price") == "0" else it.get("price"),
                    "" if hi == "0" else hi,
                    "" if close == "0" else close)
            self.tree.insert("", "end", values=vals, tags=tags)
        self.chip.config(text="当前时间数据：%d  ▤ %d条" % (self.ym, len(rows)))
        self._set_sum(sum_h, sum_e)
        self.after(30, self._layout_foot)

    def _set_sum(self, h, e):
        for lbl, v in ((self.f_h, h), (self.f_e, e)):
            if v is None:
                lbl.config(text="", background="#e9ecef", foreground="#333")
            else:
                lbl.config(text=pill_text(v), background=UP if v >= 0 else DOWN,
                           foreground="white")

    # ------------------------------------------------------------ 布局
    def apply_scale(self, f):
        self.scale = f
        self.foot_h = int(round(30 * f)) + 6
        self.foot.configure(height=self.foot_h)
        self.tree.configure(height=max(5, int(round(12 / max(1.0, f * 0.9)))))
        for c, w in zip(COLS, self._col_widths()):
            self.tree.column(c, width=w, minwidth=int(w * 0.9))
        self.after(10, self._layout_foot)

    def _col_widths(self):
        """按当前字体实测宽度计算列宽, 保证任何缩放下不截断"""
        try:
            fmain = tkfont.Font(font="AppMain")
            fhead = tkfont.Font(font="AppHead")
        except tk.TclError:
            fmain = tkfont.Font(family="微软雅黑", size=10)
            fhead = fmain.copy()
        samples = ["20260901", "000000", "中航成飞", "105.97",
                   "105.97[10.28%]", "105.97[10.28%]"]
        ws = [fmain.measure(t) + 20 for t in samples]
        ws[2] = max(ws[2], fmain.measure("中航成飞中国") + 20)
        ws = [max(w, fhead.measure(h) + 26) for w, h in zip(ws, HEADS)]
        return ws

    def _layout_foot(self):
        kids = self.tree.get_children()
        xs, ws = None, None
        if kids:
            boxes = [self.tree.bbox(kids[0], column=c) for c in COLS]
            if all(boxes):
                xs = [b[0] for b in boxes]
                ws = [b[2] for b in boxes]
        if xs is None:
            xs = [int(sum(WIDTHS[:i]) * self.scale) for i in range(6)]
            ws = [int(w * self.scale) for w in WIDTHS]
        h = max(20, self.foot_h - 8)
        self.f_title.place(x=xs[0], y=3, height=h, width=max(90, xs[3] - xs[0]))
        self.f_h.place(x=xs[4], y=3, height=h, width=ws[4])
        self.f_e.place(x=xs[5], y=3, height=h, width=ws[5])

    # ------------------------------------------------------------ 右键菜单
    def _menu(self, event):
        item = self.tree.identify_row(event.y)
        if not item:
            return
        self.tree.selection_set(item)
        vals = self.tree.item(item, "values")
        if len(vals) < 3 or not str(vals[1]).isdigit():
            return
        code, name = str(vals[1]), str(vals[2])
        menu = tk.Menu(self, tearoff=0, font="AppMain")
        menu.add_command(label="♥  加入自选  %s %s" % (code, name),
                         command=lambda: self.app.add_watch(code, name))
        menu.add_command(label="⧉  复制代码", command=lambda: self.app.copy(code))
        menu.add_command(label="⇱  浏览器打开行情",
                         command=lambda: self.app.open_web(code))
        menu.tk_popup(event.x_root, event.y_root)


# ------------------------------------------------------------------ 说明面板
class DescPanel(tb.Frame):
    """右侧策略方法说明(两端对齐, 随窗体缩放)"""

    def __init__(self, master, app):
        super().__init__(master, padding=0)
        self.scale = 1.0
        card = tb.Labelframe(self, text="  ✦ 策略方法说明  ", bootstyle="info", padding=(9, 7))
        card.pack(fill="both", expand=True)
        card.columnconfigure(0, weight=1)
        card.rowconfigure(3, weight=1)

        tb.Label(card, text=DESC_TITLE, bootstyle="danger", font="AppHead",
                 anchor="w").grid(row=0, column=0, sticky="ew", pady=(0, 6))
        link = tb.Label(card, text="⛓  %s" % QR_URL, bootstyle="info", font="AppMono",
                        cursor="hand2", anchor="w")
        link.grid(row=1, column=0, sticky="ew", pady=(0, 6))
        link.bind("<Button-1>", lambda e: app.open_web_url(QR_URL))
        tb.Separator(card).grid(row=2, column=0, sticky="ew")

        wrap = tb.Frame(card)
        wrap.grid(row=3, column=0, sticky="nsew", pady=(8, 0))
        wrap.columnconfigure(0, weight=1)
        wrap.rowconfigure(0, weight=1)
        self.cv = tk.Canvas(wrap, bg="white", highlightthickness=0)
        sb = tb.Scrollbar(wrap, orient="vertical", command=self.cv.yview,
                          bootstyle="round-info")
        self.cv.configure(yscrollcommand=sb.set)
        sb.grid(row=0, column=1, sticky="ns")
        self.cv.grid(row=0, column=0, sticky="nsew")
        self.cv.bind("<Configure>", lambda e: self.render())

    def apply_scale(self, f):
        self.scale = f
        self.after(10, self.render)

    def render(self):
        cv = self.cv
        cv.delete("all")
        w = cv.winfo_width()
        if w < 60:
            return
        size = max(8, int(round(11 * self.scale)))
        font = tkfont.Font(family="微软雅黑", size=size)
        pad = int(10 * self.scale)
        gap = int(5 * self.scale)
        indent = int(16 * self.scale)
        maxw = w - pad * 2 - indent
        if maxw < 60:
            return
        y = pad
        colors = ["#2b6cb0", "#2b6cb0", "#c0392b"]
        for pi, para in enumerate(DESC_TEXT.split("\n")):
            cv.create_text(pad, y + 2, text="▍", anchor="nw", font=font, fill=colors[pi])
            lines, cur = [], ""
            for ch in para:
                if cur and font.measure(cur + ch) > maxw:
                    lines.append(cur)
                    cur = ch
                else:
                    cur += ch
            if cur:
                lines.append(cur)
            for i, ln in enumerate(lines):
                last = (i == len(lines) - 1)
                extra = 0 if last else (maxw - font.measure(ln)) / max(1, len(ln) - 1)
                x = pad + indent
                for ch in ln:
                    cv.create_text(x, y, text=ch, anchor="nw", font=font, fill="#3b4252")
                    x += font.measure(ch) + extra
                y += font.metrics("linespace") + gap
            y += int(11 * self.scale)
        cv.configure(scrollregion=(0, 0, w, y + pad))


# ------------------------------------------------------------------ 主窗口
class App(tb.Window):
    def __init__(self):
        super().__init__(themename="cosmo")
        init_fonts()
        self.title("龙头复盘神器 · 高端策略")
        w, h = self._default_size()
        self.geometry("%dx%d" % (w, h))
        self.minsize(1200, 700)
        self.queue = queue.Queue()
        self._scale = 0
        self._build()
        self.after(120, self._poll)
        self.bind("<Configure>", self._on_resize)
        self.after(50, lambda: self._apply_scale(self._factor()))
        self._status("● 数据加载中…")

    @staticmethod
    def _default_size():
        """默认尺寸 = 设计基准尺寸(适度放大)"""
        return DESIGN_W, DESIGN_H

    def _build(self):
        # 顶部标题栏
        bar = tb.Frame(self, bootstyle="primary", padding=(14, 9))
        bar.pack(fill="x")
        tb.Label(bar, text="✦", bootstyle="inverse-primary", font="AppIcon").pack(
            side="left", padx=(0, 7))
        tb.Label(bar, text="龙头复盘神器", bootstyle="inverse-primary",
                 font="AppTitle").pack(side="left")
        tb.Label(bar, text=" · 高端策略", bootstyle="inverse-primary",
                 font="AppMain").pack(side="left")
        self.btn_refresh = tb.Button(bar, text="⟳ 全部刷新", bootstyle="success-outline",
                                     command=self.refresh)
        self.btn_refresh.pack(side="right")
        tb.Label(bar, text="⚡ 数据 · 仅供参考", bootstyle="inverse-primary",
                 font="AppMain").pack(side="right", padx=14)

        main = tb.Frame(self, padding=9)
        main.pack(fill="both", expand=True)
        for c, wt in enumerate((5, 5, 3)):
            main.columnconfigure(c, weight=wt, uniform="grp")
        main.rowconfigure(1, weight=1)
        main.rowconfigure(2, weight=1)

        t0, p0, th0 = STRATEGIES[0]
        self.p0 = StrategyPanel(main, t0, p0, th0, self)
        self.p0.grid(row=1, column=0, rowspan=2, sticky="nsew", padx=(0, 7))
        t1, p1, th1 = STRATEGIES[1]
        self.p1 = StrategyPanel(main, t1, p1, th1, self)
        self.p1.grid(row=1, column=1, sticky="nsew", padx=(0, 7), pady=(0, 7))
        t2, p2, th2 = STRATEGIES[2]
        self.p2 = StrategyPanel(main, t2, p2, th2, self)
        self.p2.grid(row=2, column=1, sticky="nsew", padx=(0, 7))
        self.panels = (self.p0, self.p1, self.p2)
        self.desc = DescPanel(main, self)
        self.desc.grid(row=1, column=2, rowspan=2, sticky="nsew")

        self.status = tb.Label(self, text="", bootstyle="secondary-inverse",
                               padding=(10, 5), anchor="w", font="AppMain")
        self.status.pack(fill="x", side="bottom")

    # ---------------------------------------------------------- 缩放
    def _factor(self):
        try:
            w, h = self.winfo_width(), self.winfo_height()
        except tk.TclError:
            return 1.0
        if w < 200 or h < 200:
            return 1.0
        f = min(w / float(DESIGN_W), h / float(DESIGN_H))
        return max(0.85, min(1.75, f))

    def _on_resize(self, event=None):
        if event and (event.widget is not self):
            return
        f = self._factor()
        if abs(f - self._scale) < 0.03:
            return
        self._apply_scale(f)

    def _apply_scale(self, f):
        self._scale = f
        for k, v in BASE_SIZE.items():
            try:
                NAMED[k].configure(size=max(8, int(round(v * f))))
            except tk.TclError:
                pass
        # 各控件样式统一使用具名字体
        st = self.style
        st.configure(".", font="AppMain")
        st.configure("Treeview", font="AppMain", rowheight=int(30 * f))
        st.configure("Treeview.Heading", font="AppHead")
        st.configure("TLabelframe.Label", font="AppHead")
        st.configure("TButton", font="AppMain")
        for p in getattr(self, "panels", ()):
            p.apply_scale(f)
        if hasattr(self, "desc"):
            self.desc.apply_scale(f)
        self.after(60, lambda: [p._layout_foot() for p in self.panels])

    # ---------------------------------------------------------- 任务队列
    def bg(self, fn, done):
        def worker():
            try:
                self.queue.put(("ok", done, fn()))
            except FileNotFoundError:
                self.queue.put(("ok", done, None))
            except Exception as e:
                self.queue.put(("err", done, str(e)))
        threading.Thread(target=worker, daemon=True).start()

    def _poll(self):
        try:
            while True:
                state, done, val = self.queue.get_nowait()
                if state == "err":
                    self._status("⚠ 接口错误: %s" % val)
                else:
                    done(val)
        except queue.Empty:
            pass
        self.after(120, self._poll)

    def _status(self, text):
        self.status.config(text="%s        %s" % (
            text, dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")))

    def refresh(self):
        for p in self.panels:
            p.load()
        self._status("⟳ 已刷新")

    # ---------------------------------------------------------- 自选股
    def _watch_path(self):
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), WATCH_FILE)

    def add_watch(self, code, name):
        path = self._watch_path()
        lines = []
        if os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                lines = [ln.strip() for ln in f if ln.strip()]
        item = "%s %s" % (code, name)
        if item not in lines:
            lines.insert(0, item)
            with open(path, "w", encoding="utf-8") as f:
                f.write("\n".join(lines))
        self._status("♥ 已加入自选: %s %s" % (code, name))

    def copy(self, text):
        self.clipboard_clear()
        self.clipboard_append(text)
        self._status("⧉ 已复制 %s" % text)

    def open_web(self, code):
        self.open_web_url("https://basic.10jqka.com.cn/" + code)

    def open_web_url(self, url):
        import webbrowser
        webbrowser.open(url)


if __name__ == "__main__":
    App().mainloop()
