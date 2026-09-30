# -*- coding: utf-8 -*-
"""ASCII-mon Studio: turn any Pokemon into an ASCII-art wallpaper."""
import ctypes
import json
import os
import random
import threading
import time
import urllib.request
import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance, ImageTk

HOME = os.path.expanduser("~")
OUTDIR = os.path.join(HOME, "Pictures", "ASCIImon")
ARTDIR = os.path.join(OUTDIR, "art")
LIBRARY = os.path.join(OUTDIR, "library.json")
os.makedirs(ARTDIR, exist_ok=True)

STYLES = {
    "Cream (Cinccino)": {"bg": (18, 16, 14), "ink": (214, 203, 186), "sub": (150, 138, 122)},
    "Amber Terminal":   {"bg": (16, 12, 6),  "ink": (255, 176, 0),   "sub": (170, 116, 0)},
    "Matrix Green":     {"bg": (5, 12, 6),   "ink": (51, 255, 102),  "sub": (30, 150, 60)},
    "Ice Blue":         {"bg": (8, 12, 18),  "ink": (168, 216, 255), "sub": (100, 140, 180)},
    "Rose":             {"bg": (18, 10, 14), "ink": (255, 183, 197), "sub": (170, 110, 125)},
    "Cyber Purple":     {"bg": (14, 8, 22),  "ink": (196, 148, 255), "sub": (130, 95, 180)},
    "Sunset":           {"bg": (22, 12, 8),  "ink": (255, 138, 76),  "sub": (180, 95, 55)},
    "Game Boy":         {"bg": (15, 31, 23), "ink": (155, 188, 15),  "sub": (100, 125, 10)},
    "Great Ball Red":   {"bg": (20, 8, 8),   "ink": (255, 92, 92),   "sub": (170, 60, 60)},
    "Deep Ocean":       {"bg": (4, 10, 16),  "ink": (72, 198, 214),  "sub": (45, 130, 145)},
    "Paper White":      {"bg": (235, 231, 222), "ink": (60, 56, 50), "sub": (120, 114, 104)},
    "Obsidian":         {"bg": (4, 4, 5),    "ink": (190, 190, 195), "sub": (110, 110, 118)},
    "Void Black":       {"bg": (0, 0, 0),    "ink": (90, 90, 95),    "sub": (55, 55, 60)},
    "Eclipse":          {"bg": (2, 2, 4),    "ink": (120, 110, 140), "sub": (70, 65, 85)},
    "Blood Moon":       {"bg": (5, 2, 2),    "ink": (150, 40, 40),   "sub": (95, 28, 28)},
    "Ghost White":      {"bg": (3, 3, 3),    "ink": (235, 235, 240), "sub": (140, 140, 148)},
}
CHARS = " .:-=+*#%@"
API = "https://pokeapi.co/api/v2/pokemon/{}"
ART = "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/{}.png"
UA = {"User-Agent": "ASCIImonStudio/1.0 (desktop wallpaper generator)"}
RECENTS_MAX = 24

THEMES = {
    "dark": {"bg": "#121110", "panel": "#1c1916", "btn": "#2a2622", "btn_hover": "#3a342e",
             "fg": "#d6cbba", "fg_dim": "#6e6459", "fg_head": "#e8ddcb", "tab_bg": "#1c1916",
             "tab_fg": "#8a7f70", "tab_sel_bg": "#2a2622", "tab_sel_fg": "#d6cbba"},
    "light": {"bg": "#f2efe9", "panel": "#e6e1d7", "btn": "#d8d2c6", "btn_hover": "#c8c1b3",
              "fg": "#3c3832", "fg_dim": "#8d8578", "fg_head": "#2a2620", "tab_bg": "#e6e1d7",
              "tab_fg": "#8d8578", "tab_sel_bg": "#d8d2c6", "tab_sel_fg": "#3c3832"},
}


def pick_font(size):
    for p in (r"C:\Windows\Fonts\consola.ttf", r"C:\Windows\Fonts\lucon.ttf", r"C:\Windows\Fonts\cour.ttf"):
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except OSError:
                pass
    return ImageFont.load_default()


def load_library():
    try:
        with open(LIBRARY, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            data.setdefault("favorites", {})
            data.setdefault("recents", [])
            return data
    except Exception:
        pass
    return {"favorites": {}, "recents": []}


def save_library(lib):
    try:
        with open(LIBRARY, "w", encoding="utf-8") as f:
            json.dump(lib, f, indent=2)
    except Exception:
        pass


def fetch_pokemon(query):
    """Return (id, name) for a name or dex number."""
    q = query.strip().lower().replace(" ", "-")
    req = urllib.request.Request(API.format(q if not q.isdigit() else int(q)), headers=UA)
    with urllib.request.urlopen(req, timeout=8) as r:
        data = json.load(r)
    return data["id"], data["name"]


def download_art(pid):
    """Download official artwork (cached). Returns RGBA Image."""
    path = os.path.join(ARTDIR, f"{pid}.png")
    if not os.path.exists(path):
        req = urllib.request.Request(ART.format(pid), headers=UA)
        with urllib.request.urlopen(req, timeout=15) as r, open(path, "wb") as f:
            f.write(r.read())
    return Image.open(path).convert("RGBA")


def make_wallpaper(pid, name, style_key, out_w=1920, out_h=1080, subtitle="official ascii edition", cols=None):
    st = STYLES[style_key]
    art = download_art(pid)

    bg = Image.new("RGB", (out_w, out_h), st["bg"])
    glow = Image.new("L", (out_w, out_h), 0)
    d = ImageDraw.Draw(glow)
    d.ellipse([out_w * 0.30, out_h * 0.15, out_w * 0.70, out_h * 0.85], fill=45)
    glow = glow.filter(ImageFilter.GaussianBlur(300))
    bg = Image.composite(Image.new("RGB", (out_w, out_h), tuple(min(255, c + 18) for c in st["bg"])), bg, glow)

    # ascii-ify (composited on bg color so transparency = dark)
    target_h = int(out_h * 0.82)
    aspect = art.height / art.width
    if cols is None:
        cols = max(40, min(170, int(target_h / (aspect * 10))))
    cols = max(30, min(160, int(cols)))   # slider range: chunky retro .. fine detail
    cell_w, cell_h = 10, 18
    rows = max(1, int(cols * aspect * (cell_w / cell_h)))
    flat = Image.new("RGBA", art.size, st["bg"] + (255,))
    flat.alpha_composite(art)
    small = flat.convert("L").resize((cols, rows), Image.LANCZOS)
    small = ImageEnhance.Contrast(small).enhance(1.45)
    small = ImageEnhance.Brightness(small).enhance(1.15)
    n = len(CHARS) - 1
    grid = ["".join(CHARS[int(n * small.getpixel((x, y)) / 255 + 0.5)] for x in range(cols)) for y in range(rows)]

    font = pick_font(max(12, out_w // 137))
    tile_w, tile_h = cols * cell_w, rows * cell_h
    x0 = min(int(out_w * 0.62) - tile_w // 2, out_w - tile_w - 60)
    y0 = (out_h - tile_h) // 2

    layer = Image.new("L", (out_w, out_h), 0)
    ld = ImageDraw.Draw(layer)
    for j, line in enumerate(grid):
        ld.text((x0, y0 + j * cell_h), line, font=font, fill=255)
    bg.paste(Image.new("RGB", (out_w, out_h), tuple(min(255, c + 40) for c in st["ink"])), (0, 0), layer.filter(ImageFilter.GaussianBlur(4)))
    bg.paste(Image.new("RGB", (out_w, out_h), st["ink"]), (0, 0), layer)

    big, smallf = pick_font(out_w // 27), pick_font(out_w // 69)
    td = ImageDraw.Draw(bg)
    ty = int(out_h * 0.40)
    td.text((int(out_w * 0.073), ty), name.upper(), font=big, fill=tuple(min(255, c + 18) for c in st["ink"]))
    td.rectangle([int(out_w * 0.075), ty + int(out_h * 0.077), int(out_w * 0.20), ty + int(out_h * 0.079)], fill=st["sub"])
    sub_text = subtitle.strip()
    line = f"#{pid:03d} - {sub_text}" if sub_text else f"#{pid:03d}"
    td.text((int(out_w * 0.075), ty + int(out_h * 0.093)), line, font=smallf, fill=st["sub"])

    out = os.path.join(OUTDIR, f"ascii_{pid:03d}_{style_key.split()[0].lower()}.png")
    bg.save(out)
    return out


def set_wallpaper(path):
    ctypes.windll.user32.SystemParametersInfoW(20, 0, path, 3)


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("ASCII-mon Studio")
        self.geometry("980x760")
        self.configure(bg="#121110")
        self.resizable(False, False)
        self.out_path = None
        self.current = None          # dict entry for the pokemon on screen
        self.lib = load_library()
        self._thumbs = {}            # keep PhotoImage refs alive
        self.dark = True             # start in dark mode

        self.style = ttk.Style(self)
        self.style.theme_use("clam")
        self._apply_theme(widgets_ready=False)

        head = ttk.Frame(self)
        head.pack(fill="x", padx=20, pady=(14, 0))
        self.head_lbl = ttk.Label(head, text="ASCII-mon Studio", style="Header.TLabel")
        self.head_lbl.pack(anchor="w", side="left")
        self.theme_btn = ttk.Button(head, text="Light mode", command=self.toggle_theme, width=12)
        self.theme_btn.pack(side="right")
        self.tag_lbl = ttk.Label(head, text="any pokemon -> ascii wallpaper", foreground="#6e6459")
        self.tag_lbl.pack(anchor="w", side="bottom")

        self.nb = ttk.Notebook(self)
        self.nb.pack(fill="both", expand=True, padx=12, pady=(8, 12))

        self.tab_gen = ttk.Frame(self.nb, padding=16)
        self.tab_fav = ttk.Frame(self.nb, padding=16)
        self.tab_rec = ttk.Frame(self.nb, padding=16)
        self.nb.add(self.tab_gen, text="Generate")
        self.nb.add(self.tab_fav, text="Favorites (0)")
        self.nb.add(self.tab_rec, text="Recents (0)")
        self._build_gen_tab()
        self._build_grid_tab(self.tab_fav, favorited=True)
        self._build_grid_tab(self.tab_rec, favorited=False)
        self._apply_theme(widgets_ready=True)   # second pass: recolor buttons/canvas now that they exist
        self.refresh_tabs()

    # ---------- theme ----------
    def toggle_theme(self):
        self.dark = not self.dark
        self._apply_theme()

    def _apply_theme(self, widgets_ready=True):
        t = THEMES["dark" if self.dark else "light"]
        self.configure(bg=t["bg"])
        s = self.style
        s.configure("TFrame", background=t["bg"])
        s.configure("TLabel", background=t["bg"], foreground=t["fg"], font=("Consolas", 11))
        s.configure("TButton", background=t["btn"], foreground=t["fg"], font=("Consolas", 11))
        s.map("TButton", background=[("active", t["btn_hover"])])
        s.configure("TEntry", fieldbackground=t["panel"], foreground=t["fg"], font=("Consolas", 12))
        s.configure("TRadiobutton", background=t["bg"], foreground=t["fg"], font=("Consolas", 10))
        s.configure("Header.TLabel", font=("Consolas", 18, "bold"), foreground=t["fg_head"])
        s.configure("TNotebook", background=t["bg"], borderwidth=0)
        s.configure("TNotebook.Tab", background=t["tab_bg"], foreground=t["tab_fg"],
                    font=("Consolas", 11), padding=(14, 6))
        s.map("TNotebook.Tab", background=[("selected", t["tab_sel_bg"])],
              foreground=[("selected", t["tab_sel_fg"])])
        if widgets_ready:
            self.theme_btn.config(text="Light mode" if self.dark else "Dark mode")
        if not widgets_ready:
            return
        for tab in (self.tab_fav, self.tab_rec):
            if hasattr(tab, "inner"):
                tab.inner.configure(style="TFrame")
                canvas = tab.inner.master
                canvas.configure(bg=t["bg"])
                for w in tab.inner.winfo_children():
                    if isinstance(w, tk.Canvas):
                        w.configure(bg=t["bg"])
        self._recolor_labels(self, t)

    def _recolor_labels(self, widget, t):
        for w in widget.winfo_children():
            if isinstance(w, ttk.Label):
                try:
                    if w.cget("foreground") in ("#6e6459", "#b0a99c"):
                        w.configure(foreground=t["fg_dim"])
                except tk.TclError:
                    pass
            self._recolor_labels(w, t)

    # ---------- generate tab ----------
    def _build_gen_tab(self):
        left = ttk.Frame(self.tab_gen)
        left.pack(side="left", fill="y")

        row = ttk.Frame(left)
        row.pack(anchor="w", fill="x")
        ttk.Label(row, text="Pokemon:").pack(side="left")
        self.entry = ttk.Entry(row, width=18)
        self.entry.pack(side="left", padx=8)
        self.entry.insert(0, "cinccino")
        self.entry.bind("<Return>", lambda e: self.generate())
        self.go = ttk.Button(row, text="Generate", command=self.generate)
        self.go.pack(side="left")
        self.lucky = ttk.Button(row, text="Surprise me", command=self.surprise)
        self.lucky.pack(side="left", padx=(6, 0))

        ttk.Label(left, text="Subtitle text:").pack(anchor="w", pady=(14, 4))
        self.sub_entry = ttk.Entry(left, width=28)
        self.sub_entry.pack(anchor="w", fill="x")
        self.sub_entry.insert(0, "official ascii edition")

        ttk.Label(left, text="ASCII detail:").pack(anchor="w", pady=(14, 4))
        drow = ttk.Frame(left)
        drow.pack(anchor="w", fill="x")
        self.detail_var = tk.DoubleVar(value=90)
        self.detail_scale = ttk.Scale(drow, from_=40, to=160, variable=self.detail_var,
                                      orient="horizontal", command=self._detail_changed)
        self.detail_scale.pack(side="left", fill="x", expand=True)
        self.detail_label = ttk.Label(drow, text="90", width=4)
        self.detail_label.pack(side="left", padx=(8, 0))
        self.detail_scale.bind("<ButtonRelease-1>", lambda e: self.generate())

        ttk.Label(left, text="Style:").pack(anchor="w", pady=(14, 4))
        self.style_var = tk.StringVar(value="Cream (Cinccino)")
        sgrid = ttk.Frame(left)
        sgrid.pack(anchor="w", fill="x")
        for i, k in enumerate(STYLES):
            rb = ttk.Radiobutton(sgrid, text=k, value=k, variable=self.style_var, command=self.generate)
            rb.grid(row=i // 2, column=i % 2, sticky="w", padx=(0, 10))

        btns = ttk.Frame(left)
        btns.pack(anchor="w", pady=(16, 6), fill="x")
        self.heart = ttk.Button(btns, text="\u2661 Favorite", command=self.toggle_favorite, state="disabled")
        self.heart.pack(side="left", fill="x", expand=True)
        self.wp_btn = ttk.Button(btns, text="Set as wallpaper", command=self.apply, state="disabled")
        self.wp_btn.pack(side="left", padx=(6, 0), fill="x", expand=True)
        self.status = ttk.Label(left, text="type a name and hit Generate", foreground="#6e6459")
        self.status.pack(anchor="w")

        right = ttk.Frame(self.tab_gen)
        right.pack(side="right", fill="both", expand=True, padx=(16, 0))
        self.preview = ttk.Label(right, text="preview appears here", anchor="center")
        self.preview.pack(fill="both", expand=True)

    # ---------- favorites / recents tabs ----------
    def _build_grid_tab(self, tab, favorited):
        canvas = tk.Canvas(tab, bg="#121110", highlightthickness=0)
        bar = ttk.Scrollbar(tab, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=bar.set)
        bar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)
        inner = ttk.Frame(canvas)
        canvas.create_window((0, 0), window=inner, anchor="nw")
        inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<MouseWheel>", lambda e: canvas.yview_scroll(-int(e.delta / 120), "units"))
        tab.inner = inner
        tab.favorited = favorited
        ttk.Label(inner, text="nothing here yet - generate something!"
                  if favorited else "nothing here yet - your rolls will show up here",
                  foreground="#6e6459").pack(anchor="w", pady=8)

    def refresh_tabs(self):
        for tab in (self.tab_fav, self.tab_rec):
            for w in tab.inner.winfo_children():
                w.destroy()
        self.nb.tab(self.tab_fav, text=f"Favorites ({len(self.lib['favorites'])})")
        self.nb.tab(self.tab_rec, text=f"Recents ({len(self.lib['recents'])})")
        for tab in (self.tab_fav, self.tab_rec):
            items = list(self.lib["favorites"].values()) if tab.favorited else self.lib["recents"]
            if not items:
                ttk.Label(tab.inner, text="nothing here yet - generate something!"
                          if tab.favorited else "nothing here yet - your rolls will show up here",
                          foreground="#6e6459").pack(anchor="w", pady=8)
                continue
            grid = ttk.Frame(tab.inner)
            grid.pack(anchor="w", pady=4)
            for i, entry in enumerate(items):
                self._make_card(grid, i // 6, i % 6, entry, tab.favorited)

    def _make_card(self, grid, r, c, entry, favorited):
        cell = ttk.Frame(grid, padding=6)
        cell.grid(row=r, column=c)
        pid = entry["pid"]
        art_path = os.path.join(ARTDIR, f"{pid}.png")
        if os.path.exists(art_path):
            img = Image.open(art_path).resize((84, 84), Image.LANCZOS)
            photo = ImageTk.PhotoImage(img)
            self._thumbs[(tab_id := id(grid), pid)] = photo
            icon = ttk.Label(cell, image=photo, cursor="hand2")
        else:
            icon = ttk.Label(cell, text="\u25a1", font=("Consolas", 30), cursor="hand2")
        icon.pack()
        name = ttk.Label(cell, text=entry["name"][:12], cursor="hand2")
        name.pack()
        heart_txt = "\u2665" if (str(pid) in self.lib["favorites"]) else "\u2661"
        actions = ttk.Frame(cell)
        actions.pack()
        open_btn = ttk.Label(actions, text="open", foreground="#8a7f70", cursor="hand2")
        open_btn.pack(side="left")
        heart_lbl = ttk.Label(actions, text=heart_txt, foreground="#c9a0a0" if heart_txt == "\u2665" else "#6e6459",
                              cursor="hand2")
        heart_lbl.pack(side="left", padx=(8, 0))
        icon.bind("<Button-1>", lambda e, en=entry: self.load_entry(en))
        name.bind("<Button-1>", lambda e, en=entry: self.load_entry(en))
        open_btn.bind("<Button-1>", lambda e, en=entry: self.load_entry(en))
        heart_lbl.bind("<Button-1>", lambda e, en=entry: self.toggle_favorite(en))

    def load_entry(self, entry):
        self.nb.select(self.tab_gen)
        self.entry.delete(0, "end")
        self.entry.insert(0, str(entry["pid"]))
        self.sub_entry.delete(0, "end")
        self.sub_entry.insert(0, entry.get("subtitle", ""))
        self.style_var.set(entry.get("style", "Cream (Cinccino)"))
        self.detail_var.set(entry.get("cols", 90))
        self.detail_label.config(text=str(int(entry.get("cols", 90))))
        self.generate()

    # ---------- actions ----------
    def _detail_changed(self, _value):
        self.detail_label.config(text=str(int(float(_value))))

    def surprise(self):
        pid = random.randint(1, 1025)
        self.entry.delete(0, "end")
        self.entry.insert(0, str(pid))
        self.generate()

    def toggle_favorite(self, entry=None):
        target = entry or self.current
        if not target:
            return
        key = str(target["pid"])
        if key in self.lib["favorites"]:
            del self.lib["favorites"][key]
            self.status.config(text=f"removed {target['name'].title()} from favorites")
        else:
            self.lib["favorites"][key] = dict(target)
            self.status.config(text=f"\u2665 {target['name'].title()} favorited!")
        save_library(self.lib)
        self._sync_heart()
        self.refresh_tabs()

    def _sync_heart(self):
        if not self.current:
            return
        fav = str(self.current["pid"]) in self.lib["favorites"]
        self.heart.config(text="\u2665 Favorited" if fav else "\u2661 Favorite")

    def generate(self):
        q = self.entry.get().strip()
        if not q:
            return
        self.go.config(state="disabled")
        self.status.config(text=f"fetching {q} ...")
        threading.Thread(target=self._work, args=(q,), daemon=True).start()

    def _work(self, q):
        try:
            pid, name = fetch_pokemon(q)
            out = make_wallpaper(pid, name, self.style_var.get(),
                                 subtitle=self.sub_entry.get(),
                                 cols=int(float(self.detail_var.get())))
            self.after(0, self._done, out, name, pid, None)
        except Exception as e:
            self.after(0, self._done, None, q, 0, str(e))

    def _done(self, out, name, pid, err):
        self.go.config(state="normal")
        if err:
            self.status.config(text=f"error: {err}")
            return
        self.out_path = out
        entry = {"pid": pid, "name": name, "style": self.style_var.get(),
                 "subtitle": self.sub_entry.get(), "cols": int(float(self.detail_var.get())),
                 "file": out, "ts": time.time()}
        self.current = entry
        self.lib["recents"] = [e for e in self.lib["recents"] if e["pid"] != pid]
        self.lib["recents"].insert(0, entry)
        del self.lib["recents"][RECENTS_MAX:]
        if str(pid) in self.lib["favorites"]:
            self.lib["favorites"][str(pid)] = dict(entry)
        save_library(self.lib)
        self._sync_heart()
        self.refresh_tabs()

        self.status.config(text=f"{name.title()} (#{pid:03d}) ready -> {os.path.basename(out)}")
        self.wp_btn.config(state="normal")
        self.heart.config(state="normal")
        img = Image.open(out).resize((640, 360), Image.LANCZOS)
        self._photo = ImageTk.PhotoImage(img)
        self.preview.config(image=self._photo, text="")

    def apply(self):
        if self.out_path:
            set_wallpaper(self.out_path)
            self.status.config(text="wallpaper set! check your desktop :)")


if __name__ == "__main__":
    App().mainloop()
