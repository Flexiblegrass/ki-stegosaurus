import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

import numpy as np
from PIL import Image, ImageTk

from stego import core, crypto, metrics

try:
    import sv_ttk
    _HAS_SVTTK = True
except ImportError:
    _HAS_SVTTK = False

PALETTE = {
    "dark": {
        "accent": "#5b8def",
        "success": "#4cd97b",
        "warning": "#ffb454",
        "danger": "#ff6b6b",
        "muted": "#9aa4b2",
        "card_bg": "#1f2430",
        "border": "#33394a",
    },
    "light": {
        "accent": "#3465e0",
        "success": "#1f9d55",
        "warning": "#b5730c",
        "danger": "#d1373f",
        "muted": "#6b7280",
        "card_bg": "#f4f6fb",
        "border": "#d8dee9",
    },
}

class Card(ttk.Frame):

    def __init__(self, master, title="", icon="", **kw):
        super().__init__(master, style="AppCard.TFrame", padding=(14, 10))
        if title:
            head = ttk.Frame(self, style="AppCardBody.TFrame")
            head.pack(fill="x", anchor="w", pady=(0, 8))
            ttk.Label(head, text=f"{icon}  {title}".strip(),
                      style="CardTitle.TLabel").pack(side="left")
        self.body = ttk.Frame(self, style="AppCardBody.TFrame")
        self.body.pack(fill="both", expand=True)


class ScrollableFrame(ttk.Frame):
    """Frame yang bisa di-scroll vertikal (scrollbar + roda mouse).

    Isi widget dipasang ke `self.inner`, bukan ke frame ini.
    """

    def __init__(self, master, padding=(4, 12)):
        super().__init__(master)
        self.canvas = tk.Canvas(self, highlightthickness=0, borderwidth=0)
        self.vsb = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.vsb.set)
        self.vsb.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)

        self.inner = ttk.Frame(self.canvas, padding=padding)
        self._win = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.inner.bind("<Configure>", self._on_inner_configure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)
        self.refresh_bg()

    def refresh_bg(self):
        bg = ttk.Style().lookup("TFrame", "background") or "#1f2430"
        self.canvas.configure(bg=bg)

    def _on_inner_configure(self, _event=None):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_canvas_configure(self, event):
        # lebar isi selalu mengikuti lebar jendela
        self.canvas.itemconfigure(self._win, width=event.width)

    def scroll_units(self, units):
        # hanya scroll bila isi lebih tinggi daripada jendela
        if self.canvas.yview() != (0.0, 1.0):
            self.canvas.yview_scroll(units, "units")


def _find_scrollable(widget):
    while widget is not None:
        if isinstance(widget, ScrollableFrame):
            return widget
        widget = getattr(widget, "master", None)
    return None


class StegoApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("StegoLSB — Steganografi LSB + AES")
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f"{min(1240, sw - 60)}x{min(920, sh - 120)}")
        self.minsize(640, 420)          # jendela boleh dikecilkan; isi bisa di-scroll
        self._bind_mousewheel()

        self.theme_mode = "dark"
        self._setup_theme()

        self.cover_path = None
        self.cover_arr = None
        self.stego_arr = None
        self.msg_file = None
        self.extracted_bytes = None
        self.stego_extract_path = None
        self._thumb_refs = []
        self.m_var = tk.IntVar(value=1)          # m-bit LSB

        self._build_ui()
        self._set_status("Siap. Pilih citra cover untuk mulai menyisipkan pesan.")

    def _bind_mousewheel(self):
        def on_wheel(event):
            if isinstance(event.widget, tk.Text):     # kotak teks scroll sendiri
                return
            sf = _find_scrollable(event.widget)
            if sf is None:
                return
            if getattr(event, "num", None) == 4:
                units = -3
            elif getattr(event, "num", None) == 5:
                units = 3
            elif abs(event.delta) >= 120:             # Windows
                units = -3 * int(event.delta / 120)
            else:                                     # macOS
                units = -int(event.delta)
            sf.scroll_units(units)

        self.bind_all("<MouseWheel>", on_wheel)       # Windows & macOS
        self.bind_all("<Button-4>", on_wheel)         # Linux
        self.bind_all("<Button-5>", on_wheel)

    def _setup_theme(self):
        if _HAS_SVTTK:
            sv_ttk.set_theme(self.theme_mode)
        else:
            style = ttk.Style(self)
            try:
                style.theme_use("clam")
            except tk.TclError:
                pass
            bg = "#1f2430" if self.theme_mode == "dark" else "#f4f6fb"
            fg = "#f0f2f7" if self.theme_mode == "dark" else "#1c2230"
            self.configure(bg=bg)
            style.configure(".", background=bg, foreground=fg)

        self._apply_custom_styles()

    def _apply_custom_styles(self):
        pal = PALETTE[self.theme_mode]
        style = ttk.Style(self)
        base_bg = style.lookup("TFrame", "background") or pal["card_bg"]

        style.configure("Header.TFrame", background=base_bg)
        style.configure("App.TLabel", font=("Segoe UI", 20, "bold"))
        style.configure("Sub.TLabel", foreground=pal["muted"],
                         font=("Segoe UI", 10))
        style.configure("AppCard.TFrame", background=pal["card_bg"],
                         relief="solid", borderwidth=1)
        style.configure("AppCardBody.TFrame", background=pal["card_bg"],
                         relief="flat", borderwidth=0)
        style.configure("CardTitle.TLabel", background=pal["card_bg"],
                         font=("Segoe UI", 11, "bold"))
        style.configure("Field.TLabel", background=pal["card_bg"],
                         font=("Segoe UI", 10))
        style.configure("Hint.TLabel", background=pal["card_bg"],
                         foreground=pal["muted"], font=("Segoe UI", 9))
        style.configure("Badge.TLabel", background=pal["card_bg"],
                         font=("Segoe UI", 9, "bold"), padding=(8, 3))
        style.configure("BadgeSuccess.TLabel", background=pal["card_bg"],
                         foreground=pal["success"], font=("Segoe UI", 9, "bold"))
        style.configure("BadgeInfo.TLabel", background=pal["card_bg"],
                         foreground=pal["accent"], font=("Segoe UI", 9, "bold"))
        style.configure("BadgeWarn.TLabel", background=pal["card_bg"],
                         foreground=pal["warning"], font=("Segoe UI", 9, "bold"))
        style.configure("Stat.TLabel", background=pal["card_bg"],
                         font=("Segoe UI", 15, "bold"))
        style.configure("StatCaption.TLabel", background=pal["card_bg"],
                         foreground=pal["muted"], font=("Segoe UI", 8, "bold"))
        style.configure("Preview.TLabel", background=pal["card_bg"],
                         anchor="center", font=("Segoe UI", 10))
        style.configure("Status.TLabel", foreground=pal["muted"],
                         font=("Segoe UI", 9))
        style.configure("Big.TButton", font=("Segoe UI", 11, "bold"),
                         padding=(14, 10))
        style.configure("Ghost.TButton", padding=(10, 6))

        self._pal = pal

    def toggle_theme(self):
        self.theme_mode = "light" if self.theme_mode == "dark" else "dark"
        if _HAS_SVTTK:
            sv_ttk.set_theme(self.theme_mode)
        self._apply_custom_styles()
        for sf in (self.tab_embed_sf, self.tab_extract_sf):
            sf.refresh_bg()
        self.theme_btn.config(text=self._theme_icon())

        self._refresh_dynamic_labels()

    def _theme_icon(self):
        return "☀️  Terang" if self.theme_mode == "dark" else "🌙  Gelap"

    def _refresh_dynamic_labels(self):
        if self.cover_arr is not None:
            cap = core.capacity_bytes(self.cover_arr, self._m())
            self._set_capacity_badge(cap)
        if getattr(self, "_last_stats", None):
            self._render_result_stats(*self._last_stats)

    def _build_ui(self):
        outer = ttk.Frame(self, padding=16)
        outer.pack(fill="both", expand=True)

        header = ttk.Frame(outer, style="Header.TFrame")
        header.pack(fill="x", pady=(0, 12))
        title_box = ttk.Frame(header, style="Header.TFrame")
        title_box.pack(side="left")
        ttk.Label(title_box, text="🪶 StegoLSB", style="App.TLabel").pack(anchor="w")
        ttk.Label(title_box, text="Steganografi LSB (m-bit)  +  Enkripsi AES",
                  style="Sub.TLabel").pack(anchor="w")

        self.theme_btn = ttk.Button(header, text=self._theme_icon(),
                                     style="Ghost.TButton",
                                     command=self.toggle_theme)
        self.theme_btn.pack(side="right", anchor="ne")

        nb = ttk.Notebook(outer)
        nb.pack(fill="both", expand=True)
        self.tab_embed_sf = ScrollableFrame(nb)
        self.tab_extract_sf = ScrollableFrame(nb)
        self.tab_embed = self.tab_embed_sf.inner
        self.tab_extract = self.tab_extract_sf.inner
        nb.add(self.tab_embed_sf, text="  🔒  Sisip Pesan  ")
        nb.add(self.tab_extract_sf, text="  🔓  Ekstrak Pesan  ")
        self._build_embed_tab()
        self._build_extract_tab()

        status_bar = ttk.Frame(outer)
        status_bar.pack(fill="x", pady=(10, 0))
        ttk.Separator(status_bar).pack(fill="x", pady=(0, 6))
        self.status_lbl = ttk.Label(status_bar, text="", style="Status.TLabel")
        self.status_lbl.pack(anchor="w")

    def _set_status(self, text):
        self.status_lbl.config(text=f"ℹ️  {text}")

    def _build_embed_tab(self):
        f = self.tab_embed
        f.columnconfigure(0, weight=1)
        f.columnconfigure(1, weight=1)

        card_cover = Card(f, "Citra Cover", "🖼️")
        card_cover.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 8))
        row = ttk.Frame(card_cover.body, style="AppCardBody.TFrame")
        row.pack(fill="x")
        ttk.Button(row, text="Pilih Citra (PNG / BMP)", style="Big.TButton",
                   command=self.pick_cover).pack(side="left")
        info = ttk.Frame(row, style="AppCardBody.TFrame")
        info.pack(side="left", padx=14)
        self.lbl_cover = ttk.Label(info, text="Belum ada citra dipilih",
                                    style="CardTitle.TLabel")
        self.lbl_cover.pack(anchor="w")
        self.lbl_cap = ttk.Label(info, text="", style="BadgeInfo.TLabel")
        self.lbl_cap.pack(anchor="w")

        card_msg = Card(f, "Pesan yang Disisipkan", "✉️")
        card_msg.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 8))
        self.txt_msg = tk.Text(card_msg.body, height=3, wrap="word",
                                relief="flat", padx=10, pady=8,
                                font=("Segoe UI", 10))
        self.txt_msg.pack(fill="x")
        file_row = ttk.Frame(card_msg.body, style="AppCardBody.TFrame")
        file_row.pack(fill="x", pady=(8, 0))
        ttk.Button(file_row, text="📎  ...atau pilih berkas",
                   style="Ghost.TButton",
                   command=self.pick_msg_file).pack(side="left")
        self.lbl_msgfile = ttk.Label(file_row, text="(pakai teks di atas)",
                                      style="Hint.TLabel")
        self.lbl_msgfile.pack(side="left", padx=10)

        card_sec = Card(f, "Keamanan", "🔑")
        card_sec.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(0, 8))
        sec = card_sec.body
        sec.columnconfigure(1, weight=1)
        sec.columnconfigure(3, weight=1)
        ttk.Label(sec, text="Kata sandi (AES):", style="Field.TLabel"
                  ).grid(row=0, column=0, sticky="w", pady=3)
        self.ent_pw = ttk.Entry(sec, show="●")
        self.ent_pw.grid(row=0, column=1, sticky="we", padx=(6, 6))
        self._add_reveal_button(sec, self.ent_pw, row=0, col=2)

        ttk.Label(sec, text="Stego-key (posisi):", style="Field.TLabel"
                  ).grid(row=0, column=3, sticky="w", padx=(16, 0))
        self.ent_key = ttk.Entry(sec, show="●")
        self.ent_key.grid(row=0, column=4, sticky="we", padx=(6, 6))
        self._add_reveal_button(sec, self.ent_key, row=0, col=5)

        ttk.Label(sec, text="Bit per kanal (m):", style="Field.TLabel"
                  ).grid(row=1, column=0, sticky="w", pady=(6, 0))
        cb_m = ttk.Combobox(sec, textvariable=self.m_var, values=[1, 2, 3, 4],
                            state="readonly", width=4)
        cb_m.grid(row=1, column=1, sticky="w", padx=(6, 6), pady=(6, 0))
        cb_m.bind("<<ComboboxSelected>>", lambda e: self._on_m_change())
        ttk.Label(sec, text="m=1 LSB biasa (paling tak terlihat). m naik → kapasitas naik, "
                            "PSNR turun.", style="Hint.TLabel"
                  ).grid(row=1, column=3, columnspan=3, sticky="w", padx=(16, 0), pady=(6, 0))

        action_row = ttk.Frame(f)
        action_row.grid(row=3, column=0, columnspan=2, pady=(2, 12))
        ttk.Button(action_row, text="🔐  Sisip  &  Simpan Stego",
                   style="Big.TButton",
                   command=self.do_embed).pack(side="left", padx=(0, 10))
        ttk.Button(action_row, text="🔬  Bidang LSB & Histogram",
                   style="Big.TButton",
                   command=self.do_steganalisis).pack(side="left")

        prev = ttk.Frame(f)
        prev.grid(row=4, column=0, columnspan=2, sticky="nsew")
        f.rowconfigure(4, weight=1)
        prev.columnconfigure(0, weight=1)
        prev.columnconfigure(1, weight=1)
        prev.rowconfigure(0, weight=1)

        card_c = Card(prev, "COVER", "📷")
        card_c.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        self.cv_cover = ttk.Label(card_c.body, text="Belum ada citra",
                                   style="Preview.TLabel", anchor="center")
        self.cv_cover.pack(fill="both", expand=True)

        card_s = Card(prev, "STEGO", "🕵️")
        card_s.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
        self.cv_stego = ttk.Label(card_s.body, text="Belum dibuat",
                                   style="Preview.TLabel", anchor="center")
        self.cv_stego.pack(fill="both", expand=True)

        self.stat_card = Card(f, "Hasil Penyisipan", "📊")
        self.stat_card.grid(row=5, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        self.stats_row = ttk.Frame(self.stat_card.body, style="AppCardBody.TFrame")
        self.stats_row.pack(fill="x")
        self.lbl_stat_placeholder = ttk.Label(
            self.stats_row, text="Belum ada hasil, sisipkan pesan terlebih dahulu.",
            style="Hint.TLabel")
        self.lbl_stat_placeholder.pack(anchor="w")
        self._last_stats = None

    def _add_reveal_button(self, parent, entry, row, col):
        def toggle():
            entry.config(show="" if entry.cget("show") else "●")
        ttk.Button(parent, text="👁", width=3, style="Ghost.TButton",
                   command=toggle).grid(row=row, column=col, sticky="w")

    def _build_extract_tab(self):
        f = self.tab_extract
        f.columnconfigure(0, weight=1)

        card_stego = Card(f, "Citra Stego", "🖼️")
        card_stego.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        row = ttk.Frame(card_stego.body, style="AppCardBody.TFrame")
        row.pack(fill="x")
        ttk.Button(row, text="Pilih Citra Stego", style="Big.TButton",
                   command=self.pick_stego).pack(side="left")
        self.lbl_stego = ttk.Label(row, text="Belum ada citra dipilih",
                                    style="CardTitle.TLabel")
        self.lbl_stego.pack(side="left", padx=14)

        card_sec = Card(f, "Kunci", "🔑")
        card_sec.grid(row=1, column=0, sticky="ew", pady=(0, 8))
        sec = card_sec.body
        sec.columnconfigure(1, weight=1)
        sec.columnconfigure(3, weight=1)
        ttk.Label(sec, text="Kata sandi (AES):", style="Field.TLabel"
                  ).grid(row=0, column=0, sticky="w")
        self.ent_pw2 = ttk.Entry(sec, show="●")
        self.ent_pw2.grid(row=0, column=1, sticky="we", padx=6)
        self._add_reveal_button(sec, self.ent_pw2, row=0, col=2)

        ttk.Label(sec, text="Stego-key:", style="Field.TLabel"
                  ).grid(row=0, column=3, sticky="w", padx=(16, 0))
        self.ent_key2 = ttk.Entry(sec, show="●")
        self.ent_key2.grid(row=0, column=4, sticky="we", padx=6)
        self._add_reveal_button(sec, self.ent_key2, row=0, col=5)

        ttk.Button(f, text="🔓  EKSTRAK PESAN", style="Big.TButton",
                   command=self.do_extract).grid(row=2, column=0, pady=(2, 12), sticky="w")

        card_out = Card(f, "Hasil Pesan", "📄")
        card_out.grid(row=3, column=0, sticky="nsew")
        f.rowconfigure(3, weight=1)
        self.lbl_extract_info = ttk.Label(card_out.body, text="",
                                           style="BadgeSuccess.TLabel")
        self.lbl_extract_info.pack(anchor="w", pady=(0, 6))
        self.txt_out = tk.Text(card_out.body, height=12, wrap="word",
                                relief="flat", padx=10, pady=8,
                                font=("Segoe UI", 10))
        self.txt_out.pack(fill="both", expand=True)
        ttk.Button(card_out.body, text="💾  Simpan hasil sebagai berkas...",
                   style="Ghost.TButton",
                   command=self.save_extracted).pack(pady=(8, 0), anchor="w")

    def pick_cover(self):
        path = filedialog.askopenfilename(
            filetypes=[("Citra PNG/BMP", "*.png *.bmp"), ("Semua", "*.*")])
        if not path:
            return
        self.cover_path = path
        self.cover_arr = core.load_image_rgb(path)
        cap = core.capacity_bytes(self.cover_arr, self._m())
        h, w, _ = self.cover_arr.shape
        self.lbl_cover.config(text=f"{os.path.basename(path)}   •   {w}×{h}px")
        self._set_capacity_badge(cap)
        self._show(self.cv_cover, self.cover_arr)
        self.cv_stego.config(image="", text="Belum dibuat")
        self._clear_stats()
        self._set_status(f"Citra cover dimuat: {os.path.basename(path)} "
                          f"(kapasitas ~{cap} byte).")

    def _m(self):
        try:
            return int(self.m_var.get())
        except (ValueError, tk.TclError):
            return 1

    def _on_m_change(self):
        if self.cover_arr is not None:
            self._set_capacity_badge(core.capacity_bytes(self.cover_arr, self._m()))

    def _set_capacity_badge(self, cap):
        self.lbl_cap.config(
            text=f"📦  Kapasitas payload: ~{cap} byte  (m = {self._m()})")

    def pick_msg_file(self):
        path = filedialog.askopenfilename(title="Pilih berkas untuk disisipkan")
        if path:
            self.msg_file = path
            self.lbl_msgfile.config(text=f"📎 {os.path.basename(path)}")
            self._set_status(f"Berkas pesan dipilih: {os.path.basename(path)}")

    def do_embed(self):
        if self.cover_arr is None:
            messagebox.showwarning("Perhatian", "Pilih citra cover dulu.")
            return
        pw = self.ent_pw.get()
        key = self.ent_key.get()
        if not pw or not key:
            messagebox.showwarning("Perhatian", "Isi kata sandi dan stego-key.")
            return

        if self.msg_file:
            with open(self.msg_file, "rb") as fp:
                message = fp.read()
        else:
            message = self.txt_msg.get("1.0", "end-1c").encode("utf-8")
        if not message:
            messagebox.showwarning("Perhatian", "Pesan kosong.")
            return

        self._set_status("Menyisipkan pesan...")
        self.update_idletasks()
        try:
            self.stego_arr = core.embed(self.cover_arr, message, pw, key, self._m())
        except core.CapacityError as e:
            messagebox.showerror("Kapasitas tidak cukup", str(e))
            self._set_status("Gagal: kapasitas citra tidak cukup.")
            return
        except Exception as e:
            messagebox.showerror("Error", str(e))
            self._set_status("Gagal menyisipkan pesan.")
            return

        out = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG", "*.png"), ("BMP", "*.bmp")],
            initialfile="stego.png")
        if not out:
            self._set_status("Penyimpanan dibatalkan.")
            return
        core.save_image(self.stego_arr, out)
        self._show(self.cv_stego, self.stego_arr)

        ps = metrics.psnr(self.cover_arr, self.stego_arr)
        ms = metrics.mse(self.cover_arr, self.stego_arr)
        chg = metrics.changed_pixels_percent(self.cover_arr, self.stego_arr)
        ukuran_asli = len(message)
        ukuran_enc = len(crypto.encrypt(message, pw))

        self._last_stats = (ps, ms, chg, ukuran_asli, ukuran_enc, out, self._m())
        self._render_result_stats(*self._last_stats)
        self._set_status(f"Berhasil disimpan: {os.path.basename(out)}  "
                          f"(m = {self._m()}, PSNR {ps:.2f} dB).")
        messagebox.showinfo(
            "Berhasil — Hasil Penyisipan",
            f"Pesan berhasil disisipkan dan disimpan.\n\n"
            f"Nama file      : {os.path.basename(out)}\n"
            f"Bit per kanal  : m = {self._m()}\n"
            f"Ukuran pesan   : {ukuran_asli} byte (asli)\n"
            f"                 {ukuran_enc} byte (setelah dienkripsi)\n"
            f"PSNR           : {ps:.2f} dB\n"
            f"MSE            : {ms:.5f}\n"
            f"Δ Kanal        : {chg:.3f}%")

    def do_steganalisis(self):
        if self.cover_arr is None or self.stego_arr is None:
            messagebox.showwarning(
                "Perhatian",
                "Sisipkan pesan dulu (klik Sisip & Simpan Stego), "
                "baru tampilkan histogram & bidang LSB-nya.")
            return
        try:
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt
        except ImportError:
            messagebox.showerror(
                "matplotlib belum ada",
                "Fitur ini butuh matplotlib.\n\nInstal dulu di terminal:\n"
                "    pip install matplotlib")
            return

        cover, stego = self.cover_arr, self.stego_arr
        ps = metrics.psnr(cover, stego)
        chg = metrics.changed_pixels_percent(cover, stego)
        hc, hs = metrics.histogram(cover), metrics.histogram(stego)
        x = np.arange(256)
        pal = getattr(self, "_pal", PALETTE["dark"])

        fig, ax = plt.subplots(2, 2, figsize=(9, 7))
        ax[0, 0].bar(x, hc, width=1.0, color=pal["accent"])
        ax[0, 0].set_title("Histogram Cover")
        ax[0, 0].set_xlabel("Nilai byte (0-255)"); ax[0, 0].set_ylabel("Frekuensi")
        ax[0, 1].bar(x, hs, width=1.0, color=pal["danger"])
        ax[0, 1].set_title("Histogram Stego")
        ax[0, 1].set_xlabel("Nilai byte (0-255)"); ax[0, 1].set_ylabel("Frekuensi")
        ax[1, 0].imshow(metrics.lsb_plane(cover))
        ax[1, 0].set_title("Bidang LSB Cover"); ax[1, 0].axis("off")
        ax[1, 1].imshow(metrics.lsb_plane(stego))
        ax[1, 1].set_title("Bidang LSB Stego (ada pesan)"); ax[1, 1].axis("off")
        fig.suptitle(f"Steganalisis Visual   |   PSNR = {ps:.2f} dB   |   "
                     f"kanal berubah = {chg:.3f}%", fontweight="bold")
        fig.tight_layout()
        out_png = "steganalisis_gui.png"
        fig.savefig(out_png, dpi=110)
        plt.close(fig)

        win = tk.Toplevel(self)
        win.title("Hasil Steganalisis Visual")
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        win.geometry(f"{min(960, sw - 80)}x{min(820, sh - 120)}")
        win.minsize(400, 300)
        sf = ScrollableFrame(win, padding=(8, 8))
        sf.pack(fill="both", expand=True)
        img = Image.open(out_png)
        img.thumbnail((900, 720))
        tkimg = ImageTk.PhotoImage(img)
        self._thumb_refs.append(tkimg)
        ttk.Label(sf.inner, image=tkimg).pack(padx=8, pady=8)
        ttk.Label(sf.inner,
                  text=f"Tersimpan sebagai {out_png}.  Histogram cover & stego "
                       f"hampir sama (PSNR {ps:.2f} dB); bidang LSB stego "
                       f"berubah karena berisi pesan.",
                  wraplength=880).pack(padx=8, pady=(0, 8))
        self._set_status(f"Histogram & bidang LSB ditampilkan (disimpan {out_png}).")

    def _clear_stats(self):
        for w in self.stats_row.winfo_children():
            w.destroy()
        self.lbl_stat_placeholder = ttk.Label(
            self.stats_row, text="Belum ada hasil, sisipkan pesan terlebih dahulu.",
            style="Hint.TLabel")
        self.lbl_stat_placeholder.pack(anchor="w")
        self._last_stats = None

    def _render_result_stats(self, ps, ms, chg, ukuran_asli, ukuran_enc, out, m=1):
        for w in self.stats_row.winfo_children():
            w.destroy()

        def stat(caption, value, style):
            box = ttk.Frame(self.stats_row, style="AppCardBody.TFrame")
            box.pack(side="left", padx=(0, 26))
            ttk.Label(box, text=caption, style="StatCaption.TLabel").pack(anchor="w")
            ttk.Label(box, text=value, style=style).pack(anchor="w")

        ps_style = "BadgeSuccess.TLabel" if ps >= 30 else "BadgeWarn.TLabel"
        stat("UKURAN PESAN", f"{ukuran_asli} B  →  {ukuran_enc} B (enc)", "BadgeInfo.TLabel")
        stat("BIT/KANAL (m)", str(m), "BadgeInfo.TLabel")
        stat("PSNR", f"{ps:.2f} dB", ps_style)
        stat("MSE", f"{ms:.5f}", "BadgeInfo.TLabel")
        stat("Δ KANAL", f"{chg:.3f}%", "BadgeInfo.TLabel")
        stat("DISIMPAN SEBAGAI", os.path.basename(out), "BadgeSuccess.TLabel")

    def pick_stego(self):
        path = filedialog.askopenfilename(
            filetypes=[("Citra PNG/BMP", "*.png *.bmp"), ("Semua", "*.*")])
        if path:
            self.stego_extract_path = path
            self.lbl_stego.config(text=os.path.basename(path))
            self._set_status(f"Citra stego dipilih: {os.path.basename(path)}")

    def do_extract(self):
        if not self.stego_extract_path:
            messagebox.showwarning("Perhatian", "Pilih citra stego dulu.")
            return
        self._set_status("Mengekstrak pesan...")
        self.update_idletasks()
        try:
            data = core.extract_from_file(
                self.stego_extract_path, self.ent_pw2.get(), self.ent_key2.get())
        except core.ExtractionError as e:
            messagebox.showerror("Gagal", str(e))
            self._set_status("Ekstraksi gagal: stego-key mungkin salah.")
            return
        except crypto.DecryptionError as e:
            messagebox.showerror("Gagal", str(e))
            self._set_status("Ekstraksi gagal: kata sandi salah.")
            return
        except Exception as e:
            messagebox.showerror("Error", str(e))
            self._set_status("Terjadi error saat ekstraksi.")
            return
        self.extracted_bytes = data
        self.txt_out.delete("1.0", "end")
        n_char = None
        try:
            teks = data.decode("utf-8")
            self.txt_out.insert("1.0", teks)
            n_char = len(teks)
        except UnicodeDecodeError:
            self.txt_out.insert("1.0",
                f"[Berkas biner {len(data)} byte — gunakan 'Simpan hasil'.]")

        info = f"✅  Ekstraksi berhasil   •   Ukuran pesan: {len(data)} byte"
        if n_char is not None:
            info += f"  ({n_char} karakter)"
        self.lbl_extract_info.config(text=info)
        self._set_status(f"Berhasil mengekstrak {len(data)} byte pesan.")
        messagebox.showinfo(
            "Berhasil — Hasil Ekstraksi",
            f"Pesan berhasil diekstrak dan diverifikasi (tag AES-GCM valid).\n\n"
            f"Ukuran pesan   : {len(data)} byte"
            + (f"  ({n_char} karakter)" if n_char is not None else "")
            + "\n\nCatatan: PSNR/MSE/Δ Kanal hanya dihitung saat penyisipan,\n"
              "karena memerlukan citra asli (cover) sebagai pembanding.")

    def save_extracted(self):
        if not self.extracted_bytes:
            return
        out = filedialog.asksaveasfilename(initialfile="pesan_hasil")
        if out:
            with open(out, "wb") as fp:
                fp.write(self.extracted_bytes)
            self._set_status(f"Hasil disimpan ke {out}")
            messagebox.showinfo("Tersimpan", out)

    # ---------------- util tampilan ----------------
    def _show(self, widget, arr, maxside=420):
        img = Image.fromarray(arr.astype(np.uint8), "RGB")
        img.thumbnail((maxside, maxside))
        tkimg = ImageTk.PhotoImage(img)
        self._thumb_refs.append(tkimg)
        widget.config(image=tkimg, text="")


if __name__ == "__main__":
    StegoApp().mainloop()