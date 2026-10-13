import tkinter as tk
from tkinter import ttk, messagebox
import urllib.request
import json
import threading
import io

# Intentamos importar pygame para el audio, si no está avisamos cómo instalarlo
try:
    import pygame
    PYGAME_AVAILABLE = True
except ImportError:
    PYGAME_AVAILABLE = False

# --- CONFIGURACIÓN DE BANDAS ---
BANDS = {
    "FM": {"min": 87.5, "max": 108.0, "step": 0.1, "unit": "MHz", "decimals": 1, "default": 98.5},
    "AM": {"min": 530, "max": 1700, "step": 10, "unit": "kHz", "decimals": 0, "default": 910},
    "OC": {"min": 3.00, "max": 30.00, "step": 0.05, "unit": "MHz", "decimals": 2, "default": 15.20}
}

COUNTRIES = ["Todos (Global)", "Argentina", "España", "México", "Colombia", "Chile", "Uruguay", "Estados Unidos"]

class RadioBacoDesktop:
    def __init__(self, root):
        self.root = root
        self.root.title("Radio Universal - Baco Edition")
        self.root.geometry("500\\times650")
        self.root.configure(bg="#0f172a")
        
        self.current_band = "FM"
        self.current_freq = 98.5
        self.selected_country = ""
        self.stations = []
        self.is_playing = False
        self.dance_frame = 0

        if PYGAME_AVAILABLE:
            pygame.mixer.init()

        self.setup_styles()
        self.create_widgets()
        self.fetch_stations()
        self.animate_baco()

    def setup_styles(self):
        self.style = ttk.Style()
        self.style.theme_use("clam")
        self.style.configure(".", background="#0f172a", foreground="#f8fafc")

    def create_widgets(self):
        # Header / Título
        header_frame = tk.Frame(self.root, bg="#020617", padx=15, pady=15)
        header_frame.pack(fill=tk.X)

        title_lbl = tk.Label(header_frame, text="📻 RADIO UNIVERSAL", font=("Inter", 14, "bold"), fg="#38bdf8", bg="#020617")
        title_lbl.pack(side=tk.LEFT)

        # Marco Principal de Visualización y Baco
        display_frame = tk.Frame(self.root, bg="#1e293b", padx=15, pady=15, relief=tk.RAISED, bd=1)
        display_frame.pack(fill=tk.X, padx=15, pady=10)

        # 🐢 BACO (Tortuga bailarina)
        self.baco_lbl = tk.Label(display_frame, text="🐢", font=("Arial", 36), bg="#1e293b")
        self.baco_lbl.pack(side=tk.RIGHT, padx=10)

        freq_info_frame = tk.Frame(display_frame, bg="#1e293b")
        freq_info_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.freq_lbl = tk.Label(freq_info_frame, text="98.5 MHz", font=("JetBrains Mono", 26, "bold"), fg="#38bdf8", bg="#1e293b")
        self.freq_lbl.pack(anchor="w")

        self.status_lbl = tk.Label(freq_info_frame, text="Baco está listo para bailar 🐢", font=("Inter", 10), fg="#94a3b8", bg="#1e293b")
        self.status_lbl.pack(anchor="w", pady=2)

        # Selector de Bandas (FM, AM, OC)
        band_frame = tk.Frame(self.root, bg="#0f172a", padx=15)
        band_frame.pack(fill=tk.X, pady=5)

        tk.Label(band_frame, text="BANDA:", font=("Inter", 9, "bold"), fg="#64748b", bg="#0f172a").pack(anchor="w")
        
        btn_bands_frame = tk.Frame(band_frame, bg="#0f172a")
        btn_bands_frame.pack(fill=tk.X, pady=2)

        for b in ["FM", "AM", "OC"]:
            btn = tk.Button(btn_bands_frame, text=b, font=("Inter", 10, "bold"), bg="#334155", fg="white", 
                            activebackground="#38bdf8", activeforeground="#0f172a", relief=tk.FLAT, width=10,
                            command=lambda band=b: self.set_band(band))
            btn.pack(side=tk.LEFT, padx=2, expand=True, fill=tk.X)

        # Dial Slider
        slider_frame = tk.Frame(self.root, bg="#0f172a", padx=15, pady=5)
        slider_frame.pack(fill=tk.X)

        tk.Label(slider_frame, text="DIAL SINTONIZADOR:", font=("Inter", 9, "bold"), fg="#64748b", bg="#0f172a").pack(anchor="w")
        self.dial_slider = tk.Scale(slider_frame, from_=0, to=100, orient=tk.HORIZONTAL, bg="#1e293b", fg="#38bdf8", 
                                    highlightthickness=0, troughcolor="#334155", command=self.on_slider_move)
        self.dial_slider.set(50)
        self.dial_slider.pack(fill=tk.X, pady=5)

        # Botón Play / Pause principal
        self.play_btn = tk.Button(self.root, text="▶ REPRODUCIR", font=("Inter", 12, "bold"), bg="#38bdf8", fg="#020617",
                                  relief=tk.FLAT, pady=10, command=self.toggle_play)
        self.play_btn.pack(fill=tk.X, padx=15, pady=10)

        # Lista de Emisoras
        list_frame = tk.Frame(self.root, bg="#0f172a", padx=15, pady=5)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        tk.Label(list_frame, text="ESTACIONES DISPONIBLES:", font=("Inter", 9, "bold"), fg="#64748b", bg="#0f172a").pack(anchor="w")
        
        self.station_listbox = tk.Listbox(list_frame, bg="#1e293b", fg="white", selectbackground="#38bdf8", 
                                          selectforeground="#0f172a", font=("Inter", 10), relief=tk.FLAT, bd=0)
        self.station_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.station_listbox.bind("<<ListboxSelect>>", self.on_station_select)

        scrollbar = tk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.station_listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.station_listbox.config(yscrollcommand=scrollbar.set)

    def set_band(self, band):
        self.current_band = band
        cfg = BANDS[band]
        self.current_freq = cfg["default"]
        self.freq_lbl.config(text=f"{self.current_freq} {cfg['unit']}")
        self.fetch_stations()

    def on_slider_move(self, val):
        cfg = BANDS[self.current_band]
        v = float(val) / 100.0
        span = cfg["max"] - cfg["min"]
        self.current_freq = round(cfg["min"] + (v * span), cfg["decimals"])
        self.freq_lbl.config(text=f"{self.current_freq} {cfg['unit']}")

    def fetch_stations(self):
        def task():
            url = "https://de1.api.radio-browser.info/json/stations/search?limit=30&hidebroken=true&order=clickcount&reverse=true"
            try:
                req = urllib.request.Request(url, headers={'User-Agent': 'RadioBacoDesktop/1.0'})
                with urllib.request.urlopen(req) as response:
                    data = json.loads(response.read().decode())
                    self.stations = [st for st in data if st.get('url_resolved') and st['url_resolved'].startswith('https://')]
                    
                    # Actualizar lista en la interfaz principal de manera segura
                    self.root.after(0, self.update_listbox)
            except Exception as e:
                pass

        threading.Thread(target=task, daemon=True).start()

    def update_listbox(self):
        self.station_listbox.delete(0, tk.END)
        for st in self.stations:
            self.station_listbox.insert(tk.END, f"{st.get('name', 'Radio')} ({st.get('country', 'Mundial')})")

    def on_station_select(self, event):
        selection = self.station_listbox.curselection()
        if selection:
            idx = selection[0]
            st = self.stations[idx]
            self.play_station(st)

    def play_station(self, station):
        if not PYGAME_AVAILABLE:
            messagebox.showerror("Error", "Falta la librería pygame. Instalala con: pip install pygame")
            return
        
        url = station['url_resolved']
        self.status_lbl.config(text=f"🐢🎵 Sonando: {station.get('name', 'Radio')}")
        self.is_playing = True
        self.play_btn.config(text="⏸ PAUSAR")

        def play_stream():
            try:
                pygame.mixer.music.load(url)
                pygame.mixer.music.play()
            except Exception as e:
                self.root.after(0, lambda: self.status_lbl.config(text="❌ Error al reproducir stream"))

        threading.Thread(target=play_stream, daemon=True).start()

    def toggle_play(self):
        if not PYGAME_AVAILABLE:
            messagebox.showerror("Error", "Falta la librería pygame. Instalala con: pip install pygame")
            return

        if self.is_playing:
            pygame.mixer.music.pause()
            self.is_playing = False
            self.play_btn.config(text="▶ REPRODUCIR")
            self.status_lbl.config(text="🐢 Baco descansando...")
        else:
            if pygame.mixer.music.get_busy():
                pygame.mixer.music.unpause()
                self.is_playing = True
                self.play_btn.config(text="⏸ PAUSAR")
                self.status_lbl.config(text="🐢🎵 Baco bailando de nuevo")
            elif self.stations:
                self.play_station(self.stations[0])

    def animate_baco(self):
        # Animación de Baco bailando si está sonando música
        if self.is_playing:
            frames = ["🐢", "🕺🐢", "💃🐢", "🐢✨"]
            self.dance_frame = (self.dance_frame + 1) % len(frames)
            self.baco_lbl.config(text=frames[self.dance_frame])
        else:
            self.baco_lbl.config(text="🐢")
        
        self.root.after(400, self.animate_baco)

if __name__ == "__main__":
    root = tk.Tk()
    app = RadioBacoDesktop(root)
    root.mainloop()