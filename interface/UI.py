import tkinter as tk
from tkinter import ttk, font
import time
import threading
import platform
import psutil  # Para información del sistema (opcional)

# No se requieren dependencias externas si usamos solo tkinter estándar.
# Si deseas agregar gráficos avanzados o widgets modernos puedes usar:
# customtkinter==5.2.0
# matplotlib==3.8.0
# psutil==5.9.5
# geopy==2.4.0

# =============================
# CONFIGURACIÓN VISUAL GENERAL
# =============================

BG_COLOR = "#0d0d0d"  # Fondo oscuro
GRID_COLOR = "#00ffff"  # Cyan brillante para rejillas
TEXT_COLOR = "#ffffff"  # Texto blanco
ACCENT_COLOR = "#ffcc00"  # Dorado steampunk
FONT_FAMILY = "Courier New"
FONT_SIZE = 10


# =============================
# CLASE PRINCIPAL DE LA INTERFAZ
# =============================

class RetroFuturisticUI:
    def __init__(self, root):
        self.root = root
        self.root.title("RETRO-FUTURISTIC CONTROL PANEL")
        self.root.geometry("1000x700")
        self.root.configure(bg=BG_COLOR)

        # Fuente personalizada
        default_font = font.Font(family=FONT_FAMILY, size=FONT_SIZE)
        self.root.option_add("*Font", default_font)

        # Cabecera decorativa
        self.header_frame = tk.Frame(root, bg=BG_COLOR, height=60)
        self.header_frame.pack(fill=tk.X, pady=(10, 0))

        self.header_label = tk.Label(
            self.header_frame,
            text="RETRO-FUTURISTIC CONTROL INTERFACE v1.0",
            fg=GRID_COLOR,
            bg=BG_COLOR,
            font=(FONT_FAMILY, 16, "bold")
        )
        self.header_label.pack(pady=10)

        # Contenido principal dividido en paneles
        self.content_frame = tk.Frame(root, bg=BG_COLOR)
        self.content_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        # Panel izquierdo - Información del Sistema
        self.system_info_panel()

        # Panel derecho - Datos dinámicos (ejemplo: hora, agentes)
        self.dynamic_data_panel()

        # Pie de página
        self.footer_frame = tk.Frame(root, bg=BG_COLOR, height=40)
        self.footer_frame.pack(side=tk.BOTTOM, fill=tk.X)

        self.footer_label = tk.Label(
            self.footer_frame,
            text="STATUS: ACTIVE | CONNECTION: SECURE",
            fg=ACCENT_COLOR,
            bg=BG_COLOR,
            font=(FONT_FAMILY, 10)
        )
        self.footer_label.pack(pady=5)

        # Actualización automática cada segundo
        self.update_clock()

    def system_info_panel(self):
        frame = tk.LabelFrame(self.content_frame, text="SYSTEM INFO", fg=GRID_COLOR, bg=BG_COLOR, bd=2, relief="groove")
        frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10), pady=10)

        info_text = f"""
OS: {platform.system()} {platform.release()}
CPU Usage: {psutil.cpu_percent(interval=1)}%
RAM Available: {round(psutil.virtual_memory().available / (1024 * 1024 * 1024), 2)} GB
Battery: {psutil.sensors_battery().percent if hasattr(psutil, 'sensors_battery') and psutil.sensors_battery() else 'N/A'}%
Location: LAT: -- LONG: --
        """

        label = tk.Label(frame, text=info_text.strip(), justify=tk.LEFT, anchor="w", fg=TEXT_COLOR, bg=BG_COLOR)
        label.pack(padx=10, pady=10)

    def dynamic_data_panel(self):
        frame = tk.LabelFrame(self.content_frame, text="DYNAMIC DATA", fg=GRID_COLOR, bg=BG_COLOR, bd=2,
                              relief="groove")
        frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Hora actual
        self.time_label = tk.Label(frame, text="", fg=GRID_COLOR, bg=BG_COLOR, font=(FONT_FAMILY, 14))
        self.time_label.pack(anchor="nw", padx=10, pady=10)

        # Simulación de agentes de IA conectados
        agents_label = tk.Label(frame, text="AI AGENTS ONLINE:", fg=ACCENT_COLOR, bg=BG_COLOR, font=(FONT_FAMILY, 12))
        agents_label.pack(anchor="nw", padx=10, pady=(20, 5))

        agents_listbox = tk.Listbox(frame, height=6, width=50, bg="#1a1a1a", fg=TEXT_COLOR, font=(FONT_FAMILY, 10))
        agents_listbox.insert(0, "Agent Alpha [ACTIVE]")
        agents_listbox.insert(1, "Agent Beta [IDLE]")
        agents_listbox.insert(2, "Agent Gamma [PROCESSING]")
        agents_listbox.pack(padx=10, pady=5)

    def update_clock(self):
        current_time = time.strftime("%Y-%m-%d %H:%M:%S")
        self.time_label.config(text=f"CURRENT TIME: {current_time}")
        self.root.after(1000, self.update_clock)  # Llamada recursiva cada 1 segundo


# =============================
# PUNTO DE ENTRADA DEL PROGRAMA
# =============================

if __name__ == "__main__":
    root = tk.Tk()
    app = RetroFuturisticUI(root)
    root.mainloop()
