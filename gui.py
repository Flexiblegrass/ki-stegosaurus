import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

import numpy as np
from PIL import Image, ImageTk

from stego import core, crypto, metrics, audio, steganalysis

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


class StegoApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("StegoLSB — Steganografi LSB + AES")
        self.geometry("1240x920")
        self.minsize(1040, 760)

        self.theme_mode = "dark"
        self._setup_theme()

        self.cover_path = None
        self.cover_arr = None
        self.stego_arr = None
        self.msg_file = None
        self.extracted_bytes = None
        self.stego_extract_path = None
        self._thumb_refs = []

        # fitur pengayaan
        self.m_var = tk.IntVar(value=1)          # m-bit LSB (citra)
        self.m_var_audio = tk.IntVar(value=1)    # m-bit LSB (audio)
        self.wav_path = None
        self.wav_samples = None
        self.wav_params = None
        self.wav_stego_path = None
        self.audio_extracted = None
        self.chi_cover = None
        self.chi_stego = None

        self._build_ui()
        self._set_status("Siap. Pilih citra cover untuk mulai menyisipkan pesan.")

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
        ttk.Label(title_box,
                  text="Steganografi LSB (m-bit)  +  Enkripsi AES  •  Citra & Audio WAV  •  Steganalisis Chi-Square",
                  style="Sub.TLabel").pack(anchor="w")

        self.theme_btn = ttk.Button(header, text=self._theme_icon(),
                                     style="Ghost.TButton",
                                     command=self.toggle_theme)
        self.theme_btn.pack(side="right", anchor="ne")

        nb = ttk.Notebook(outer)
        nb.pack(fill="both", expand=True)
        self.tab_embed = ttk.Frame(nb, padding=(4, 12))
        self.tab_extract = ttk.Frame(nb, padding=(4, 12))
        nb.add(self.tab_embed, text="  🔒  Sisip Pesan  ")
        nb.add(self.tab_extract, text="  🔓  Ekstrak Pesan  ")
        self.tab_audio = ttk.Frame(nb, padding=(4, 12))
        self.tab_chi = ttk.Frame(nb, padding=(4, 12))
        nb.add(self.tab_audio, text="  🎵  Audio WAV  ")
        nb.add(self.tab_chi, text="  📈  Chi-Square  ")
        self._build_embed_tab()
        self._build_extract_tab()
        self._build_audio_tab()
        self._build_chi_tab()

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

    # =====================================================================
    # TAB AUDIO WAV (fitur pengayaan)
    # =====================================================================
    def _build_audio_tab(self):
        f = self.tab_audio
        f.columnconfigure(0, weight=1)

        card = Card(f, "Audio Cover (WAV PCM 8/16-bit)", "🎧")
        card.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        row = ttk.Frame(card.body, style="AppCardBody.TFrame")
        row.pack(fill="x")
        ttk.Button(row, text="Pilih Audio WAV", style="Big.TButton",
                   command=self.pick_wav).pack(side="left")
        info = ttk.Frame(row, style="AppCardBody.TFrame")
        info.pack(side="left", padx=14)
        self.lbl_wav = ttk.Label(info, text="Belum ada audio dipilih",
                                 style="CardTitle.TLabel")
        self.lbl_wav.pack(anchor="w")
        self.lbl_wav_cap = ttk.Label(info, text="", style="BadgeInfo.TLabel")
        self.lbl_wav_cap.pack(anchor="w")

        card_msg = Card(f, "Pesan yang Disisipkan", "✉️")
        card_msg.grid(row=1, column=0, sticky="ew", pady=(0, 8))
        self.txt_wav_msg = tk.Text(card_msg.body, height=3, wrap="word",
                                   relief="flat", padx=10, pady=8,
                                   font=("Segoe UI", 10))
        self.txt_wav_msg.pack(fill="x")

        card_sec = Card(f, "Keamanan", "🔑")
        card_sec.grid(row=2, column=0, sticky="ew", pady=(0, 8))
        sec = card_sec.body
        sec.columnconfigure(1, weight=1)
        sec.columnconfigure(3, weight=1)
        ttk.Label(sec, text="Kata sandi (AES):", style="Field.TLabel"
                  ).grid(row=0, column=0, sticky="w", pady=3)
        self.ent_wpw = ttk.Entry(sec, show="●")
        self.ent_wpw.grid(row=0, column=1, sticky="we", padx=(6, 6))
        self._add_reveal_button(sec, self.ent_wpw, row=0, col=2)
        ttk.Label(sec, text="Stego-key (posisi):", style="Field.TLabel"
                  ).grid(row=0, column=3, sticky="w", padx=(16, 0))
        self.ent_wkey = ttk.Entry(sec, show="●")
        self.ent_wkey.grid(row=0, column=4, sticky="we", padx=(6, 6))
        self._add_reveal_button(sec, self.ent_wkey, row=0, col=5)
        ttk.Label(sec, text="Bit per sampel (m):", style="Field.TLabel"
                  ).grid(row=1, column=0, sticky="w", pady=(6, 0))
        cb = ttk.Combobox(sec, textvariable=self.m_var_audio, values=[1, 2, 3, 4],
                          state="readonly", width=4)
        cb.grid(row=1, column=1, sticky="w", padx=(6, 6), pady=(6, 0))
        cb.bind("<<ComboboxSelected>>", lambda e: self._refresh_wav_capacity())

        ttk.Button(f, text="🔐  Sisip  &  Simpan WAV Stego", style="Big.TButton",
                   command=self.do_audio_embed).grid(row=3, column=0, sticky="w", pady=(2, 8))
        self.lbl_wav_stat = ttk.Label(f, text="", style="BadgeSuccess.TLabel")
        self.lbl_wav_stat.grid(row=4, column=0, sticky="w", pady=(0, 10))

        card_x = Card(f, "Ekstrak dari WAV Stego", "🔓")
        card_x.grid(row=5, column=0, sticky="nsew")
        f.rowconfigure(5, weight=1)
        xb = card_x.body
        xb.columnconfigure(3, weight=1)
        xb.columnconfigure(5, weight=1)
        ttk.Button(xb, text="Pilih WAV Stego", style="Ghost.TButton",
                   command=self.pick_wav_stego).grid(row=0, column=0, sticky="w")
        self.lbl_wav_stego = ttk.Label(xb, text="(belum dipilih)", style="Hint.TLabel")
        self.lbl_wav_stego.grid(row=0, column=1, columnspan=5, sticky="w", padx=8)
        ttk.Label(xb, text="Kata sandi:", style="Field.TLabel"
                  ).grid(row=1, column=0, sticky="w", pady=(8, 0))
        self.ent_wpw2 = ttk.Entry(xb, show="●")
        self.ent_wpw2.grid(row=1, column=1, columnspan=3, sticky="we", padx=6, pady=(8, 0))
        ttk.Label(xb, text="Stego-key:", style="Field.TLabel"
                  ).grid(row=1, column=4, sticky="w", padx=(16, 0), pady=(8, 0))
        self.ent_wkey2 = ttk.Entry(xb, show="●")
        self.ent_wkey2.grid(row=1, column=5, sticky="we", padx=6, pady=(8, 0))
        ttk.Button(xb, text="🔓  EKSTRAK", style="Big.TButton",
                   command=self.do_audio_extract).grid(row=2, column=0, columnspan=2,
                                                       sticky="w", pady=(10, 6))
        self.lbl_wav_out = ttk.Label(xb, text="", style="BadgeSuccess.TLabel")
        self.lbl_wav_out.grid(row=2, column=2, columnspan=4, sticky="w", padx=8)
        self.txt_wav_out = tk.Text(xb, height=5, wrap="word", relief="flat",
                                   padx=10, pady=8, font=("Segoe UI", 10))
        self.txt_wav_out.grid(row=3, column=0, columnspan=6, sticky="nsew")

    def _wm(self):
        try:
            return int(self.m_var_audio.get())
        except (ValueError, tk.TclError):
            return 1

    def _refresh_wav_capacity(self):
        if self.wav_samples is None:
            return
        cap = audio.capacity_bytes(self.wav_samples, self._wm())
        self.lbl_wav_cap.config(
            text=f"📦  Kapasitas payload: ~{cap} byte  (m = {self._wm()})")

    def pick_wav(self):
        path = filedialog.askopenfilename(
            filetypes=[("Audio WAV", "*.wav"), ("Semua", "*.*")])
        if not path:
            return
        try:
            samples, params = audio.load_wav(path)
        except audio.AudioFormatError as e:
            messagebox.showerror("Format audio tidak didukung", str(e))
            return
        self.wav_path, self.wav_samples, self.wav_params = path, samples, params
        dur = params["frames"] / params["rate"]
        self.lbl_wav.config(
            text=f"{os.path.basename(path)}   •   {params['width'] * 8}-bit, "
                 f"{params['channels']} kanal, {params['rate']} Hz, {dur:.1f} detik")
        self._refresh_wav_capacity()
        self._set_status(f"Audio cover dimuat: {os.path.basename(path)}")

    def do_audio_embed(self):
        if self.wav_samples is None:
            messagebox.showwarning("Perhatian", "Pilih audio WAV dulu.")
            return
        pw, key = self.ent_wpw.get(), self.ent_wkey.get()
        if not pw or not key:
            messagebox.showwarning("Perhatian", "Isi kata sandi dan stego-key.")
            return
        message = self.txt_wav_msg.get("1.0", "end-1c").encode("utf-8")
        if not message:
            messagebox.showwarning("Perhatian", "Pesan kosong.")
            return
        m = self._wm()
        self._set_status("Menyisipkan pesan ke audio...")
        self.update_idletasks()
        try:
            stego = audio.embed(self.wav_samples, message, pw, key, m)
        except core.CapacityError as e:
            messagebox.showerror("Kapasitas tidak cukup", str(e))
            self._set_status("Gagal: kapasitas audio tidak cukup.")
            return
        except Exception as e:
            messagebox.showerror("Error", str(e))
            return
        out = filedialog.asksaveasfilename(
            defaultextension=".wav", filetypes=[("Audio WAV", "*.wav")],
            initialfile="stego.wav")
        if not out:
            self._set_status("Penyimpanan dibatalkan.")
            return
        audio.save_wav(out, stego, self.wav_params)

        width = self.wav_params["width"]
        xs = audio.to_signed(self.wav_samples, width)
        ys = audio.to_signed(stego, width)
        sn = metrics.snr(xs, ys)
        ps = metrics.psnr(xs, ys, audio.peak_value(width))
        ms = metrics.mse(xs, ys)
        self.lbl_wav_stat.config(
            text=f"✅  Tersimpan: {os.path.basename(out)}   •   m = {m}   •   "
                 f"SNR {sn:.2f} dB   •   PSNR {ps:.2f} dB   •   MSE {ms:.4f}")
        self._set_status(f"WAV stego disimpan: {os.path.basename(out)} (SNR {sn:.2f} dB).")
        messagebox.showinfo(
            "Berhasil — Audio Stego",
            f"Pesan berhasil disisipkan ke audio.\n\n"
            f"Nama file : {os.path.basename(out)}\n"
            f"m         : {m} bit per sampel\n"
            f"SNR       : {sn:.2f} dB\nPSNR      : {ps:.2f} dB\nMSE       : {ms:.4f}")

    def pick_wav_stego(self):
        path = filedialog.askopenfilename(
            filetypes=[("Audio WAV", "*.wav"), ("Semua", "*.*")])
        if path:
            self.wav_stego_path = path
            self.lbl_wav_stego.config(text=os.path.basename(path))

    def do_audio_extract(self):
        if not self.wav_stego_path:
            messagebox.showwarning("Perhatian", "Pilih WAV stego dulu.")
            return
        try:
            data = audio.extract_from_file(
                self.wav_stego_path, self.ent_wpw2.get(), self.ent_wkey2.get())
        except (core.ExtractionError, crypto.DecryptionError, audio.AudioFormatError) as e:
            messagebox.showerror("Gagal", str(e))
            self._set_status("Ekstraksi audio gagal.")
            self.lbl_wav_out.config(text="")
            return
        except Exception as e:
            messagebox.showerror("Error", str(e))
            return
        self.audio_extracted = data
        self.txt_wav_out.delete("1.0", "end")
        try:
            self.txt_wav_out.insert("1.0", data.decode("utf-8"))
        except UnicodeDecodeError:
            self.txt_wav_out.insert("1.0", f"[Data biner {len(data)} byte]")
        self.lbl_wav_out.config(text=f"✅  Ekstraksi berhasil  •  {len(data)} byte")
        self._set_status(f"Berhasil mengekstrak {len(data)} byte dari audio.")

    # =====================================================================
    # TAB STEGANALISIS CHI-SQUARE (fitur pengayaan)
    # =====================================================================
    def _build_chi_tab(self):
        f = self.tab_chi
        f.columnconfigure(0, weight=1)
        f.columnconfigure(1, weight=1)

        card = Card(f, "Citra yang Diuji", "🔬")
        card.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 8))
        b = card.body
        ttk.Button(b, text="Pilih Citra Cover", style="Ghost.TButton",
                   command=lambda: self.pick_chi("cover")).grid(row=0, column=0, sticky="w")
        self.lbl_chi_cover = ttk.Label(b, text="(belum dipilih)", style="Hint.TLabel")
        self.lbl_chi_cover.grid(row=0, column=1, sticky="w", padx=8)
        ttk.Button(b, text="Pilih Citra Stego", style="Ghost.TButton",
                   command=lambda: self.pick_chi("stego")).grid(row=1, column=0, sticky="w", pady=(6, 0))
        self.lbl_chi_stego = ttk.Label(b, text="(belum dipilih)", style="Hint.TLabel")
        self.lbl_chi_stego.grid(row=1, column=1, sticky="w", padx=8, pady=(6, 0))
        ttk.Button(b, text="⬅  Pakai cover & stego dari tab Sisip Pesan",
                   style="Ghost.TButton", command=self.chi_use_embed_tab
                   ).grid(row=2, column=0, columnspan=2, sticky="w", pady=(8, 0))

        act = ttk.Frame(f)
        act.grid(row=1, column=0, columnspan=2, pady=(2, 10))
        ttk.Button(act, text="📈  Jalankan Uji Chi-Square", style="Big.TButton",
                   command=self.do_chi).pack(side="left", padx=(0, 10))
        ttk.Button(act, text="📊  Grafik Selisih Pasangan", style="Big.TButton",
                   command=self.do_chi_plot).pack(side="left")

        card_c = Card(f, "HASIL — COVER", "📷")
        card_c.grid(row=2, column=0, sticky="nsew", padx=(0, 6))
        self.txt_chi_cover = tk.Text(card_c.body, height=14, wrap="word", relief="flat",
                                     padx=10, pady=8, font=("Consolas", 10))
        self.txt_chi_cover.pack(fill="both", expand=True)
        card_s = Card(f, "HASIL — STEGO", "🕵️")
        card_s.grid(row=2, column=1, sticky="nsew", padx=(6, 0))
        self.txt_chi_stego = tk.Text(card_s.body, height=14, wrap="word", relief="flat",
                                     padx=10, pady=8, font=("Consolas", 10))
        self.txt_chi_stego.pack(fill="both", expand=True)
        f.rowconfigure(2, weight=1)

        ttk.Label(f, wraplength=1100, style="Sub.TLabel",
                  text="Cara baca: p-value besar (> 0,05) berarti histogram pasangan nilai (2i, 2i+1) "
                       "sudah disamaratakan → terindikasi ada penyisipan. p-value ≈ 0 → tidak terindikasi. "
                       "Uji ini hanya sensitif bila laju sisip tinggi; pada cover berderau (mis. foto sangat "
                       "berderau) bisa terjadi false positive."
                  ).grid(row=3, column=0, columnspan=2, sticky="w", pady=(10, 0))

    def pick_chi(self, which):
        path = filedialog.askopenfilename(
            filetypes=[("Citra PNG/BMP", "*.png *.bmp"), ("Semua", "*.*")])
        if not path:
            return
        arr = core.load_image_rgb(path)
        if which == "cover":
            self.chi_cover = arr
            self.lbl_chi_cover.config(text=os.path.basename(path))
        else:
            self.chi_stego = arr
            self.lbl_chi_stego.config(text=os.path.basename(path))

    def chi_use_embed_tab(self):
        if self.cover_arr is None or self.stego_arr is None:
            messagebox.showwarning(
                "Perhatian", "Sisipkan pesan dulu di tab Sisip Pesan.")
            return
        self.chi_cover, self.chi_stego = self.cover_arr, self.stego_arr
        self.lbl_chi_cover.config(text="(dari tab Sisip Pesan)")
        self.lbl_chi_stego.config(text="(dari tab Sisip Pesan)")

    @staticmethod
    def _chi_report(arr):
        res = steganalysis.analyze_image(arr)
        g = res["gabungan"]
        lines = [f"GABUNGAN (R+G+B)",
                 f"  chi-square : {g['chi2']:.2f}",
                 f"  df         : {g['df']}",
                 f"  p-value    : {g['p_value']:.4g}",
                 f"  keputusan  : {g['verdict']}", "", "PER KANAL"]
        for k in "RGB":
            if k in res:
                r = res[k]
                tag = "terindikasi" if r["flagged"] else "bersih"
                lines.append(f"  {k}: chi2={r['chi2']:.1f}  df={r['df']}  "
                             f"p={r['p_value']:.3g}  → {tag}")
        return "\n".join(lines)

    def do_chi(self):
        if self.chi_cover is None and self.chi_stego is None:
            messagebox.showwarning("Perhatian", "Pilih minimal satu citra (cover/stego).")
            return
        for arr, txt in ((self.chi_cover, self.txt_chi_cover),
                         (self.chi_stego, self.txt_chi_stego)):
            txt.delete("1.0", "end")
            txt.insert("1.0", self._chi_report(arr) if arr is not None
                       else "(citra belum dipilih)")
        self._set_status("Uji chi-square selesai.")

    def do_chi_plot(self):
        if self.chi_cover is None and self.chi_stego is None:
            messagebox.showwarning("Perhatian", "Pilih minimal satu citra (cover/stego).")
            return
        try:
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt
        except ImportError:
            messagebox.showerror("matplotlib belum ada", "pip install matplotlib")
            return
        pal = getattr(self, "_pal", PALETTE["dark"])
        items = [(a, t, c) for a, t, c in ((self.chi_cover, "Cover", pal["accent"]),
                                           (self.chi_stego, "Stego", pal["danger"]))
                 if a is not None]
        fig, ax = plt.subplots(1, len(items), figsize=(5.5 * len(items), 3.8), squeeze=False)
        for i, (arr, title, color) in enumerate(items):
            ax[0, i].bar(range(128), steganalysis.pair_difference(arr), width=1, color=color)
            ax[0, i].set_title(f"{title}: h[2i] − h[2i+1]")
            ax[0, i].set_xlabel("indeks pasangan i")
            ax[0, i].set_ylabel("selisih frekuensi")
        fig.suptitle("Penyamarataan pasangan nilai (mendekati 0 = terindikasi stego)",
                     fontweight="bold")
        fig.tight_layout()
        out_png = "chi_square_gui.png"
        fig.savefig(out_png, dpi=110)
        plt.close(fig)
        win = tk.Toplevel(self)
        win.title("Grafik Selisih Pasangan")
        img = Image.open(out_png)
        img.thumbnail((1100, 500))
        tkimg = ImageTk.PhotoImage(img)
        self._thumb_refs.append(tkimg)
        ttk.Label(win, image=tkimg).pack(padx=8, pady=8)
        self._set_status(f"Grafik chi-square ditampilkan (disimpan {out_png}).")

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
        img = Image.open(out_png)
        img.thumbnail((900, 720))
        tkimg = ImageTk.PhotoImage(img)
        self._thumb_refs.append(tkimg)
        ttk.Label(win, image=tkimg).pack(padx=8, pady=8)
        ttk.Label(win,
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
