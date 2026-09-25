import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

import numpy as np
from PIL import Image, ImageTk

from stego import core, crypto, metrics


class StegoApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("StegoLSB — Steganografi LSB + AES")
        self.geometry("1000x680")
        self.configure(padx=12, pady=12)

        self.cover_path = None
        self.cover_arr = None
        self.stego_arr = None
        self._thumb_refs = [] 

        self._build_ui()

    #  UI 
    def _build_ui(self):
        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True)
        self.tab_embed = ttk.Frame(nb, padding=10)
        self.tab_extract = ttk.Frame(nb, padding=10)
        nb.add(self.tab_embed, text="  Sisip Pesan  ")
        nb.add(self.tab_extract, text="  Ekstrak Pesan  ")
        self._build_embed_tab()
        self._build_extract_tab()

    def _build_embed_tab(self):
        f = self.tab_embed

        top = ttk.Frame(f); top.pack(fill="x")
        ttk.Button(top, text="Pilih Citra Cover (PNG/BMP)",
                   command=self.pick_cover).pack(side="left")
        self.lbl_cover = ttk.Label(top, text="Belum ada citra dipilih")
        self.lbl_cover.pack(side="left", padx=10)
        self.lbl_cap = ttk.Label(top, text="", foreground="#0a7")
        self.lbl_cap.pack(side="right")

        form = ttk.Frame(f); form.pack(fill="x", pady=8)
        ttk.Label(form, text="Pesan teks:").grid(row=0, column=0, sticky="nw")
        self.txt_msg = tk.Text(form, height=4, width=70)
        self.txt_msg.grid(row=0, column=1, columnspan=3, sticky="we", pady=3)

        ttk.Button(form, text="...atau pilih berkas",
                   command=self.pick_msg_file).grid(row=1, column=1, sticky="w")
        self.lbl_msgfile = ttk.Label(form, text="(pakai teks di atas)")
        self.lbl_msgfile.grid(row=1, column=2, columnspan=2, sticky="w")

        ttk.Label(form, text="Kata sandi (AES):").grid(row=2, column=0, sticky="w", pady=3)
        self.ent_pw = ttk.Entry(form, show="*", width=28)
        self.ent_pw.grid(row=2, column=1, sticky="w")
        ttk.Label(form, text="Stego-key (posisi):").grid(row=2, column=2, sticky="e")
        self.ent_key = ttk.Entry(form, show="*", width=24)
        self.ent_key.grid(row=2, column=3, sticky="w")

        ttk.Button(f, text="SISIP  &  SIMPAN STEGO",
                   command=self.do_embed).pack(pady=6)

        imgs = ttk.Frame(f); imgs.pack(fill="both", expand=True, pady=6)
        self.cv_cover = ttk.Label(imgs, text="COVER", relief="groove", anchor="center")
        self.cv_stego = ttk.Label(imgs, text="STEGO", relief="groove", anchor="center")
        self.cv_cover.pack(side="left", expand=True, fill="both", padx=6)
        self.cv_stego.pack(side="left", expand=True, fill="both", padx=6)
        self.lbl_psnr = ttk.Label(f, text="", font=("TkDefaultFont", 11, "bold"))
        self.lbl_psnr.pack()

        self.msg_file = None

    def _build_extract_tab(self):
        f = self.tab_extract
        top = ttk.Frame(f); top.pack(fill="x")
        ttk.Button(top, text="Pilih Citra Stego",
                   command=self.pick_stego).pack(side="left")
        self.lbl_stego = ttk.Label(top, text="Belum ada citra dipilih")
        self.lbl_stego.pack(side="left", padx=10)

        form = ttk.Frame(f); form.pack(fill="x", pady=8)
        ttk.Label(form, text="Kata sandi (AES):").grid(row=0, column=0, sticky="w")
        self.ent_pw2 = ttk.Entry(form, show="*", width=28)
        self.ent_pw2.grid(row=0, column=1, sticky="w", padx=5)
        ttk.Label(form, text="Stego-key:").grid(row=0, column=2, sticky="e")
        self.ent_key2 = ttk.Entry(form, show="*", width=24)
        self.ent_key2.grid(row=0, column=3, sticky="w", padx=5)

        ttk.Button(f, text="EKSTRAK PESAN", command=self.do_extract).pack(pady=6)
        ttk.Label(f, text="Hasil pesan:").pack(anchor="w")
        self.txt_out = tk.Text(f, height=10, width=90)
        self.txt_out.pack(fill="both", expand=True)
        ttk.Button(f, text="Simpan hasil sebagai berkas...",
                   command=self.save_extracted).pack(pady=4)
        self.extracted_bytes = None
        self.stego_extract_path = None

    #  Aksi 
    def pick_cover(self):
        path = filedialog.askopenfilename(
            filetypes=[("Citra PNG/BMP", "*.png *.bmp"), ("Semua", "*.*")])
        if not path:
            return
        self.cover_path = path
        self.cover_arr = core.load_image_rgb(path)
        cap = core.capacity_bytes(self.cover_arr)
        h, w, _ = self.cover_arr.shape
        self.lbl_cover.config(text=f"{os.path.basename(path)}  ({w}x{h})")
        self.lbl_cap.config(text=f"Kapasitas payload: ~{cap} byte")
        self._show(self.cv_cover, self.cover_arr)
        self.cv_stego.config(image="", text="STEGO")
        self.lbl_psnr.config(text="")

    def pick_msg_file(self):
        path = filedialog.askopenfilename(title="Pilih berkas untuk disisipkan")
        if path:
            self.msg_file = path
            self.lbl_msgfile.config(text=os.path.basename(path))

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
        try:
            self.stego_arr = core.embed(self.cover_arr, message, pw, key)
        except core.CapacityError as e:
            messagebox.showerror("Kapasitas tidak cukup", str(e))
            return
        except Exception as e:
            messagebox.showerror("Error", str(e))
            return

        out = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG", "*.png"), ("BMP", "*.bmp")],
            initialfile="stego.png")
        if not out:
            return
        core.save_image(self.stego_arr, out)
        self._show(self.cv_stego, self.stego_arr)
        ps = metrics.psnr(self.cover_arr, self.stego_arr)
        chg = metrics.changed_pixels_percent(self.cover_arr, self.stego_arr)
        self.lbl_psnr.config(
            text=f"PSNR = {ps:.2f} dB   |   kanal berubah = {chg:.3f}%   |   "
                 f"disimpan: {os.path.basename(out)}")
        messagebox.showinfo("Berhasil",
                            f"Pesan disisipkan.\nPSNR = {ps:.2f} dB\nFile: {out}")

    def pick_stego(self):
        path = filedialog.askopenfilename(
            filetypes=[("Citra PNG/BMP", "*.png *.bmp"), ("Semua", "*.*")])
        if path:
            self.stego_extract_path = path
            self.lbl_stego.config(text=os.path.basename(path))

    def do_extract(self):
        if not self.stego_extract_path:
            messagebox.showwarning("Perhatian", "Pilih citra stego dulu.")
            return
        try:
            data = core.extract_from_file(
                self.stego_extract_path, self.ent_pw2.get(), self.ent_key2.get())
        except core.ExtractionError as e:
            messagebox.showerror("Gagal", str(e)); return
        except crypto.DecryptionError as e:
            messagebox.showerror("Gagal", str(e)); return
        except Exception as e:
            messagebox.showerror("Error", str(e)); return
        self.extracted_bytes = data
        self.txt_out.delete("1.0", "end")
        try:
            self.txt_out.insert("1.0", data.decode("utf-8"))
        except UnicodeDecodeError:
            self.txt_out.insert("1.0",
                f"[Berkas biner {len(data)} byte — gunakan 'Simpan hasil'.]")

    def save_extracted(self):
        if not self.extracted_bytes:
            return
        out = filedialog.asksaveasfilename(initialfile="pesan_hasil")
        if out:
            with open(out, "wb") as fp:
                fp.write(self.extracted_bytes)
            messagebox.showinfo("Tersimpan", out)

    #  util tampilan 
    def _show(self, widget, arr, maxside=420):
        img = Image.fromarray(arr.astype(np.uint8), "RGB")
        img.thumbnail((maxside, maxside))
        tkimg = ImageTk.PhotoImage(img)
        self._thumb_refs.append(tkimg)
        widget.config(image=tkimg, text="")


if __name__ == "__main__":
    StegoApp().mainloop()
