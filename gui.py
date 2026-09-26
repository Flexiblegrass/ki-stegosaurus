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
    """Panel bergaya 'kartu': judul kecil + border halus + padding."""

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
        # refresh warna dinamis yang sudah ditampilkan
        self._refresh_dynamic_labels()

    def _theme_icon(self):
        return "☀️  Terang" if self.theme_mode == "dark" else "🌙  Gelap"

    def _refresh_dynamic_labels(self):
        # panggil ulang label yang punya style berwarna agar sinkron tema
        if self.cover_arr is not None:
            cap = core.capacity_bytes(self.cover_arr)
            self._set_capacity_badge(cap)
        if getattr(self, "_last_psnr_vals", None):
            self._render_result_stats(*self._last_psnr_vals)

    # ---------------- UI ----------------
    def _build_ui(self):
        outer = ttk.Frame(self, padding=16)
        outer.pack(fill="both", expand=True)

        header = ttk.Frame(outer, style="Header.TFrame")
        header.pack(fill="x", pady=(0, 12))
        title_box = ttk.Frame(header, style="Header.TFrame")
        title_box.pack(side="left")
        ttk.Label(title_box, text="🪶 StegoLSB", style="App.TLabel").pack(anchor="w")
        ttk.Label(title_box, text="Steganografi LSB  +  Enkripsi AES",
                  style="Sub.TLabel").pack(anchor="w")

        self.theme_btn = ttk.Button(header, text=self._theme_icon(),
                                     style="Ghost.TButton",
                                     command=self.toggle_theme)
        self.theme_btn.pack(side="right", anchor="ne")

        # ---- Tabs ----
        nb = ttk.Notebook(outer)
        nb.pack(fill="both", expand=True)
        self.tab_embed = ttk.Frame(nb, padding=(4, 12))
        self.tab_extract = ttk.Frame(nb, padding=(4, 12))
        nb.add(self.tab_embed, text="  🔒  Sisip Pesan  ")
        nb.add(self.tab_extract, text="  🔓  Ekstrak Pesan  ")
        self._build_embed_tab()
        self._build_extract_tab()

        # ---- Status bar ----
        status_bar = ttk.Frame(outer)
        status_bar.pack(fill="x", pady=(10, 0))
        ttk.Separator(status_bar).pack(fill="x", pady=(0, 6))
        self.status_lbl = ttk.Label(status_bar, text="", style="Status.TLabel")
        self.status_lbl.pack(anchor="w")

    def _set_status(self, text):
        self.status_lbl.config(text=f"ℹ️  {text}")

    # ---- Tab: Sisip ----
    def _build_embed_tab(self):
        f = self.tab_embed
        f.columnconfigure(0, weight=1)
        f.columnconfigure(1, weight=1)

        # Kartu 1: cover
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

        # Kartu 2: pesan
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

        # Kartu 3: keamanan
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

        # Tombol aksi utama
        ttk.Button(f, text="🔐  SISIP  &  SIMPAN STEGO", style="Big.TButton",
                   command=self.do_embed).grid(
            row=3, column=0, columnspan=2, pady=(2, 12))

        # Preview berdampingan
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

        # Kartu statistik hasil
        self.stat_card = Card(f, "Hasil Penyisipan", "📊")
        self.stat_card.grid(row=5, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        self.stats_row = ttk.Frame(self.stat_card.body, style="AppCardBody.TFrame")
        self.stats_row.pack(fill="x")
        self.lbl_stat_placeholder = ttk.Label(
            self.stats_row, text="Belum ada hasil — sisipkan pesan terlebih dahulu.",
            style="Hint.TLabel")
        self.lbl_stat_placeholder.pack(anchor="w")
        self._last_psnr_vals = None

    def _add_reveal_button(self, parent, entry, row, col):
        def toggle():
            entry.config(show="" if entry.cget("show") else "●")
        ttk.Button(parent, text="👁", width=3, style="Ghost.TButton",
                   command=toggle).grid(row=row, column=col, sticky="w")

    # ---- Tab: Ekstrak ----
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
        self.txt_out = tk.Text(card_out.body, height=12, wrap="word",
                                relief="flat", padx=10, pady=8,
                                font=("Segoe UI", 10))
        self.txt_out.pack(fill="both", expand=True)
        ttk.Button(card_out.body, text="💾  Simpan hasil sebagai berkas...",
                   style="Ghost.TButton",
                   command=self.save_extracted).pack(pady=(8, 0), anchor="w")

    # ---------------- Aksi ----------------
    def pick_cover(self):
        path = filedialog.askopenfilename(
            filetypes=[("Citra PNG/BMP", "*.png *.bmp"), ("Semua", "*.*")])
        if not path:
            return
        self.cover_path = path
        self.cover_arr = core.load_image_rgb(path)
        cap = core.capacity_bytes(self.cover_arr)
        h, w, _ = self.cover_arr.shape
        self.lbl_cover.config(text=f"{os.path.basename(path)}   •   {w}×{h}px")
        self._set_capacity_badge(cap)
        self._show(self.cv_cover, self.cover_arr)
        self.cv_stego.config(image="", text="Belum dibuat")
        self._clear_stats()
        self._set_status(f"Citra cover dimuat: {os.path.basename(path)} "
                          f"(kapasitas ~{cap} byte).")

    def _set_capacity_badge(self, cap):
        self.lbl_cap.config(text=f"📦  Kapasitas payload: ~{cap} byte")

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
        # ambil pesan: berkas jika dipilih, selain itu teks
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
            self.stego_arr = core.embed(self.cover_arr, message, pw, key)
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
        chg = metrics.changed_pixels_percent(self.cover_arr, self.stego_arr)
        self._last_psnr_vals = (ps, chg, out)
        self._render_result_stats(ps, chg, out)
        self._set_status(f"Berhasil disimpan: {os.path.basename(out)}  "
                          f"(PSNR {ps:.2f} dB).")
        messagebox.showinfo("Berhasil",
                            f"Pesan disisipkan.\nPSNR = {ps:.2f} dB\nFile: {out}")

    def _clear_stats(self):
        for w in self.stats_row.winfo_children():
            w.destroy()
        self.lbl_stat_placeholder = ttk.Label(
            self.stats_row, text="Belum ada hasil — sisipkan pesan terlebih dahulu.",
            style="Hint.TLabel")
        self.lbl_stat_placeholder.pack(anchor="w")
        self._last_psnr_vals = None

    def _render_result_stats(self, ps, chg, out):
        for w in self.stats_row.winfo_children():
            w.destroy()

        def stat(parent, caption, value, style):
            box = ttk.Frame(parent, style="AppCardBody.TFrame")
            box.pack(side="left", padx=(0, 28))
            ttk.Label(box, text=caption, style="StatCaption.TLabel"
                      ).pack(anchor="w")
            ttk.Label(box, text=value, style=style).pack(anchor="w")
            return box

        ps_style = "BadgeSuccess.TLabel" if ps >= 40 else (
            "BadgeWarn.TLabel" if ps >= 30 else "BadgeWarn.TLabel")
        stat(self.stats_row, "PSNR", f"{ps:.2f} dB", ps_style)
        stat(self.stats_row, "KANAL BERUBAH", f"{chg:.3f}%", "BadgeInfo.TLabel")
        fbox = ttk.Frame(self.stats_row, style="AppCardBody.TFrame")
        fbox.pack(side="left")
        ttk.Label(fbox, text="DISIMPAN SEBAGAI", style="StatCaption.TLabel"
                  ).pack(anchor="w")
        ttk.Label(fbox, text=os.path.basename(out), style="BadgeSuccess.TLabel"
                  ).pack(anchor="w")

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
        try:
            self.txt_out.insert("1.0", data.decode("utf-8"))
            self._set_status(f"Berhasil mengekstrak {len(data)} byte pesan teks.")
        except UnicodeDecodeError:
            self.txt_out.insert("1.0",
                f"[Berkas biner {len(data)} byte — gunakan 'Simpan hasil'.]")
            self._set_status(f"Berhasil mengekstrak {len(data)} byte data biner.")

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
