import tkinter as tk
from tkinter import font
from PIL import Image, ImageTk, ImageEnhance, ImageDraw
import os
import subprocess
import pygame
import json
import threading
import time
import sys
import requests

# === CONFIG ===
VLC_PATH = r"C:\Program Files\VideoLAN\VLC\vlc.exe"  # Pfad zu VLC anpassen
THUMBNAIL_TIME = "00:00:03"
THUMBNAIL_SIZE = (220, 124)
FILM_COVER_SIZE = (220, 330)
ANIM_SCALE = 1.1
ANIM_SPEED = 15  # ms pro Frame
ANIM_STEPS = 5
CURRENT_VERSION = "1.0"
GITHUB_VERSION_URL = "https://raw.githubusercontent.com/deinusername/deinrepo/main/version.txt"
GITHUB_EXE_URL = "https://github.com/deinusername/deinrepo/releases/latest/download/pyflix.exe"
LOCAL_EXE_PATH = sys.executable  # Pfad zur aktuell laufenden exe


pygame.mixer.init()


def check_for_update():
    try:
        response = requests.get(GITHUB_VERSION_URL, timeout=5)
        response.raise_for_status()
        latest_version = response.text.strip()
        if latest_version > CURRENT_VERSION:
            print(f"Update verfügbar: {latest_version}")
            download_update()
            return True
        else:
            print("Programm ist aktuell.")
            return False
    except Exception as e:
        print("Update-Check fehlgeschlagen:", e)
        return False

def download_update():
    try:
        r = requests.get(GITHUB_EXE_URL, stream=True)
        r.raise_for_status()
        new_exe_path = LOCAL_EXE_PATH + ".new"
        with open(new_exe_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
        # Nach Download neue Datei als neue exe umbennen und altes Programm schließen
        print("Update heruntergeladen.")
        restart_with_update(new_exe_path)
    except Exception as e:
        print("Download fehlgeschlagen:", e)

def restart_with_update(new_exe_path):
    # Auf Windows kann eine laufende exe nicht überschrieben werden,
    # deshalb starten wir einen kleinen Batch, der das neue Programm ersetzt
    batch_script = f"""
    @echo off
    timeout /t 2 /nobreak
    move /Y "{new_exe_path}" "{LOCAL_EXE_PATH}"
    start "" "{LOCAL_EXE_PATH}"
    """
    batch_file = os.path.join(os.path.dirname(LOCAL_EXE_PATH), "update.bat")
    with open(batch_file, "w") as f:
        f.write(batch_script)
    subprocess.Popen(["cmd", "/c", batch_file])
    sys.exit()
class HoverLabel(tk.Label):
    def __init__(self, master, pil_image, *args, **kwargs):
        # pil_image: PIL Image (RGBA)
        self.pil_image_original = pil_image.convert("RGBA")
        self.animating = False
        self.anim_step = 0
        self.anim_dir = 1  # Für Ping-Pong Animation des Glows
        self.glow_pos = 0
        self.tk_image = ImageTk.PhotoImage(self.pil_image_original)
        super().__init__(master, image=self.tk_image, *args, **kwargs)
        self.bind("<Enter>", self.start_animation)
        self.bind("<Leave>", self.stop_animation)

    def start_animation(self, event=None):
        if not self.animating:
            self.animating = True
            self.anim_step = 0
            self.glow_pos = 0
            self.anim_dir = 1
            self.animate()

    def animate(self):
        if not self.animating:
            # Reset auf Originalbild, wenn Hover weg
            self.tk_image = ImageTk.PhotoImage(self.pil_image_original)
            self.config(image=self.tk_image)
            return

        # Helligkeit etwas erhöhen beim Hover
        enhancer = ImageEnhance.Brightness(self.pil_image_original)
        bright_img = enhancer.enhance(1.2)

        # Glow: Ein schmaler, halbtransparenter Weiß-Gradient, der sich bewegt
        glow_width = int(bright_img.width * 0.3)
        glow = Image.new("RGBA", bright_img.size, (0, 0, 0, 0))
        for x in range(glow_width):
            alpha = int(100 * (1 - abs(x - self.glow_pos) / glow_width))
            for y in range(bright_img.height):
                px = x + self.glow_pos
                if 0 <= px < bright_img.width:
                    glow.putpixel((px, y), (255, 255, 255, alpha))

        img_with_glow = Image.alpha_composite(bright_img, glow)

        self.tk_image = ImageTk.PhotoImage(img_with_glow)
        self.config(image=self.tk_image)

        # Glow wandert vor und zurück
        self.glow_pos += self.anim_dir * 5
        if self.glow_pos <= 0 or self.glow_pos + glow_width >= bright_img.width:
            self.anim_dir *= -1

        self.after(50, self.animate)

    def stop_animation(self, event=None):
        self.animating = False

class PyFlixApp:
    def __init__(self, root):
        self.root = root
        self.root.title("PyFlix - Netflix Clone")
        self.root.geometry("1200x750")
        self.root.configure(bg="#141414")
        self.current_frame = None
        self.film_base_path = os.getcwd()
        self.playing_audio = False
        self.font_bold = font.Font(family="Helvetica", size=14, weight="bold")
        self.font_regular = font.Font(family="Helvetica", size=11)

        # Für Hintergrundbild in Episode Menu
        self.background_label = None
        self.background_img_original = None

        self.show_loading_screen()

        # Filme im Hintergrund laden, danach Hauptmenu zeigen
        threading.Thread(target=self.load_films_and_show_menu, daemon=True).start()

    def show_loading_screen(self):
        self.clear_frame()
        self.current_frame = tk.Frame(self.root, bg="#141414")
        self.current_frame.pack(fill="both", expand=True)

        loading_label = tk.Label(self.current_frame, text="PyFlix lädt...", font=("Helvetica", 30, "bold"), fg="#E50914", bg="#141414")
        loading_label.pack(expand=True)

        # Einfache Puls-Animation
        def pulse(step=0):
            color_val = 200 + int(55 * (1 + (-1)**step) / 2)  # wechselt zwischen 200 und 255
            loading_label.config(fg=f"#E5{color_val:02X}14")
            self.root.after(500, lambda: pulse(1 - step))
        pulse()

    def load_films_and_show_menu(self):
        # Simulierte Ladezeit (entfernen, wenn du möchtest)
        time.sleep(2)

        # Nach dem Laden: Hauptmenü im MainThread anzeigen
        self.root.after(0, self.show_main_menu)

    def clear_frame(self):
        if self.current_frame:
            self.current_frame.destroy()
            self.current_frame = None

    def play_audio_loop(self, audio_path):
        if os.path.exists(audio_path):
            pygame.mixer.music.load(audio_path)
            pygame.mixer.music.play(loops=-1)
            self.playing_audio = True

    def stop_audio(self):
        pygame.mixer.music.stop()
        self.playing_audio = False

    def launch_vlc(self, video_path):
        self.stop_audio()
        subprocess.Popen([VLC_PATH, "--play-and-exit", video_path])

    def show_main_menu(self):
        self.stop_audio()
        self.clear_frame()
        self.current_frame = tk.Frame(self.root, bg="#141414")
        self.current_frame.pack(fill="both", expand=True)

        title = tk.Label(self.current_frame, text="🎬 Willkommen bei PyFlix",
                        font=("Helvetica", 28, "bold"), fg="white", bg="#141414")
        title.pack(pady=25)

        film_frame = tk.Frame(self.current_frame, bg="#141414")
        film_frame.pack(padx=20, pady=10, fill="both", expand=True)

        films = [f for f in os.listdir(self.film_base_path) if os.path.isdir(f)]
        col = 0
        row = 0

        for film in films:
            cover_path = os.path.join(film, "Cover", "cover.jpg")
            if not os.path.exists(cover_path):
                continue  # Kein Cover -> überspringen

            # Bild laden und Effekte anwenden (PIL Image)
            img = Image.open(cover_path).resize(FILM_COVER_SIZE)
            img = ImageEnhance.Brightness(img).enhance(1.2)
            img = ImageEnhance.Contrast(img).enhance(1.3)

            # Netflix-Glossy Effekt:
            gloss = Image.new("RGBA", img.size)
            for y in range(img.size[1]//3):
                alpha = int(120 * (1 - y/(img.size[1]//3)))
                for x in range(img.size[0]):
                    gloss.putpixel((x, y), (255, 255, 255, alpha))
            img = Image.alpha_composite(img.convert("RGBA"), gloss)

            # Übergabe an HoverLabel: PIL Image direkt, NICHT ImageTk.PhotoImage
            lbl = HoverLabel(film_frame, img, bg="#141414", cursor="hand2")
            lbl.grid(row=row, column=col, padx=20, pady=20)
            lbl.bind("<Button-1>", lambda e, name=film: self.show_dvd_menu(name))

            # Filmtitel drunter
            tk.Label(film_frame, text=film, font=self.font_bold, fg="white", bg="#141414").grid(row=row+1, column=col, pady=(0,20))

            col += 1
            if col > 3:
                col = 0
                row += 2  # Weil Titel auch 1 Reihe beansprucht

    def show_dvd_menu(self, film_name):
        self.clear_frame()
        self.current_frame = tk.Frame(self.root, bg="#1c1c1c")
        self.current_frame.pack(fill="both", expand=True)

        audio_path = os.path.join(film_name, "Audio", "soundtrack.mp3")
        self.play_audio_loop(audio_path)

        header = tk.Frame(self.current_frame, bg="#1c1c1c")
        header.pack(pady=20, fill="x")

        tk.Label(header, text=f"🎞 {film_name}", font=("Helvetica", 24, "bold"), fg="white", bg="#1c1c1c").pack(side="left", padx=20)
        tk.Button(header, text="🔙 Zurück", font=self.font_regular, command=self.show_main_menu).pack(side="right", padx=20)

        # Buttons für alle oder Episoden
        btn_frame = tk.Frame(self.current_frame, bg="#1c1c1c")
        btn_frame.pack(pady=10)

        tk.Button(btn_frame, text="▶ Alle abspielen", font=self.font_bold, bg="#e50914", fg="white",
                  activebackground="#f40612", padx=20, pady=10,
                  command=lambda: self.play_all_videos(film_name)).grid(row=0, column=0, padx=15)

        tk.Button(btn_frame, text="📺 Episoden-Auswahl", font=self.font_bold, bg="#221f1f", fg="white",
                  activebackground="#3a3939", padx=20, pady=10,
                  command=lambda: self.show_episode_menu(film_name)).grid(row=0, column=1, padx=15)

    def play_all_videos(self, film_name):
        self.stop_audio()
        folders = sorted([f for f in os.listdir(film_name) if f.lower().startswith("video")],
                        key=lambda x: int(''.join(filter(str.isdigit, x)) or 0))
        for folder in folders:
            folder_path = os.path.join(film_name, folder)
            videos = sorted([f for f in os.listdir(folder_path) if f.endswith(".mp4")])
            for file in videos:
                video_path = os.path.join(folder_path, file)
                # Hier warten wir, bis VLC schließt, bevor das nächste Video startet:
                subprocess.run([VLC_PATH, "--play-and-exit", video_path])

    def show_episode_menu(self, film_name):
        self.clear_frame()
        self.current_frame = tk.Frame(self.root, bg="#1c1c1c")
        self.current_frame.pack(fill="both", expand=True)

        # Hintergrundbild laden
        background_path = os.path.join(film_name, "Cover", "background.jpg")
        if os.path.exists(background_path):
            self.background_img_original = Image.open(background_path).convert("RGBA")
        else:
            self.background_img_original = None

        # Canvas als Hintergrund
        self.bg_canvas = tk.Canvas(self.current_frame, bg="#1c1c1c", highlightthickness=0)
        self.bg_canvas.pack(fill="both", expand=True)
        self.bg_canvas.bind("<Configure>", self.resize_background)

        # Frame mit Scrollbar auf Canvas
        self.scroll_frame = tk.Frame(self.bg_canvas, bg="#1c1c1c")

        self.canvas_window = self.bg_canvas.create_window((0, 0), window=self.scroll_frame, anchor="nw")

        scrollbar = tk.Scrollbar(self.current_frame, orient="vertical", command=self.bg_canvas.yview)
        scrollbar.pack(side="right", fill="y")

        self.bg_canvas.configure(yscrollcommand=scrollbar.set)

        self.scroll_frame.bind(
            "<Configure>",
            lambda e: self.bg_canvas.configure(scrollregion=self.bg_canvas.bbox("all"))
        )

        # Header oben über Canvas (damit immer sichtbar)
        header = tk.Frame(self.current_frame, bg="#1c1c1c")
        header.place(relx=0, rely=0, relwidth=1)
        tk.Label(header, text="📺 Episoden-Auswahl", font=("Helvetica", 24, "bold"), fg="white", bg="#1c1c1c").pack(side="left", padx=20, pady=10)
        tk.Button(header, text="🔙 Zurück", font=self.font_regular,
                  command=lambda: self.show_dvd_menu(film_name)).pack(side="right", padx=20, pady=10)

        folders = sorted([f for f in os.listdir(film_name) if f.lower().startswith("video")],
                         key=lambda x: int(''.join(filter(str.isdigit, x)) or 0))
        row = 1  # wegen Header
        col = 0

        thumb_dir = os.path.join(film_name, "thumbnails")
        os.makedirs(thumb_dir, exist_ok=True)

        for folder in folders:
            video_folder = os.path.join(film_name, folder)
            videos = sorted([v for v in os.listdir(video_folder) if v.endswith(".mp4")])
            ep_num = 1

            for video in videos:
                video_path = os.path.join(video_folder, video)
                thumb_path = os.path.join(thumb_dir, f"{folder}_{video}.jpg")

                # Thumbnail mit ffmpeg erstellen
                if not os.path.exists(thumb_path):
                    subprocess.run([
                        "ffmpeg", "-ss", THUMBNAIL_TIME, "-i", video_path,
                        "-frames:v", "1", "-q:v", "2", thumb_path
                    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

                # Bild laden und verkleinern
                if os.path.exists(thumb_path):
                    img = Image.open(thumb_path).resize(THUMBNAIL_SIZE)

                    # Übergabe an HoverLabel: PIL Image, nicht ImageTk.PhotoImage
                    lbl_img = HoverLabel(self.scroll_frame, img, bg="#222222", cursor="hand2")
                    lbl_img.grid(row=row, column=col, padx=15, pady=15)

                    # Episoden-Nummer
                    num_lbl = tk.Label(self.scroll_frame, text=f"Episode {ep_num}", fg="white", bg="#222222",
                                       font=self.font_bold)
                    num_lbl.grid(row=row+1, column=col, sticky="w", padx=15, pady=(0,5))

                    # Beschreibung aus JSON oder TXT laden
                    desc_text = "Keine Beschreibung vorhanden."
                    desc_path_json = os.path.join(video_folder, "info.json")
                    desc_path_txt = os.path.join(video_folder, "description.txt")
                    if os.path.exists(desc_path_json):
                        try:
                            with open(desc_path_json, "r", encoding="utf-8") as f:
                                data = json.load(f)
                                desc_text = data.get("description", desc_text)
                        except Exception:
                            pass
                    elif os.path.exists(desc_path_txt):
                        try:
                            with open(desc_path_txt, "r", encoding="utf-8") as f:
                                desc_text = f.read()
                        except Exception:
                            pass

                    desc_lbl = tk.Label(self.scroll_frame, text=desc_text, wraplength=THUMBNAIL_SIZE[0],
                                        justify="left", fg="white", bg="#222222", font=self.font_regular)
                    desc_lbl.grid(row=row+2, column=col, sticky="w", padx=15, pady=(0,20))

                    # Klick-Event zum Abspielen der Episode
                    lbl_img.bind("<Button-1>", lambda e, path=video_path: self.launch_vlc(path))

                    col += 1
                    if col >= 4:
                        col = 0
                        row += 3
                    ep_num += 1

    def resize_background(self, event):
        if self.background_img_original:
            w, h = event.width, event.height
            resized = self.background_img_original.resize((w, h), Image.LANCZOS)
            self.bg_image_tk = ImageTk.PhotoImage(resized)
            # Bild als Hintergrund auf Canvas zeichnen
            self.bg_canvas.create_image(0, 0, image=self.bg_image_tk, anchor="nw")
        self.bg_canvas.config(scrollregion=self.bg_canvas.bbox("all"))

def main():
    root = tk.Tk()
    app = PyFlixApp(root)
    root.mainloop()

import tkinter as tk
from tkinter import font
from PIL import Image, ImageTk, ImageEnhance, ImageDraw
import os
import subprocess
import pygame
import json
import threading
import time
import sys
import requests

# === CONFIG ===
VLC_PATH = r"C:\Program Files\VideoLAN\VLC\vlc.exe"  # Pfad zu VLC anpassen
THUMBNAIL_TIME = "00:00:03"
THUMBNAIL_SIZE = (220, 124)
FILM_COVER_SIZE = (220, 330)
ANIM_SCALE = 1.1
ANIM_SPEED = 15  # ms pro Frame
ANIM_STEPS = 5
CURRENT_VERSION = "1.0"
GITHUB_VERSION_URL = "https://raw.githubusercontent.com/deinusername/deinrepo/main/version.txt"
GITHUB_EXE_URL = "https://github.com/deinusername/deinrepo/releases/latest/download/pyflix.exe"
LOCAL_EXE_PATH = sys.executable  # Pfad zur aktuell laufenden exe


pygame.mixer.init()


def check_for_update():
    try:
        response = requests.get(GITHUB_VERSION_URL, timeout=5)
        response.raise_for_status()
        latest_version = response.text.strip()
        if latest_version > CURRENT_VERSION:
            print(f"Update verfügbar: {latest_version}")
            download_update()
            return True
        else:
            print("Programm ist aktuell.")
            return False
    except Exception as e:
        print("Update-Check fehlgeschlagen:", e)
        return False

def download_update():
    try:
        r = requests.get(GITHUB_EXE_URL, stream=True)
        r.raise_for_status()
        new_exe_path = LOCAL_EXE_PATH + ".new"
        with open(new_exe_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
        # Nach Download neue Datei als neue exe umbennen und altes Programm schließen
        print("Update heruntergeladen.")
        restart_with_update(new_exe_path)
    except Exception as e:
        print("Download fehlgeschlagen:", e)

def restart_with_update(new_exe_path):
    # Auf Windows kann eine laufende exe nicht überschrieben werden,
    # deshalb starten wir einen kleinen Batch, der das neue Programm ersetzt
    batch_script = f"""
    @echo off
    timeout /t 2 /nobreak
    move /Y "{new_exe_path}" "{LOCAL_EXE_PATH}"
    start "" "{LOCAL_EXE_PATH}"
    """
    batch_file = os.path.join(os.path.dirname(LOCAL_EXE_PATH), "update.bat")
    with open(batch_file, "w") as f:
        f.write(batch_script)
    subprocess.Popen(["cmd", "/c", batch_file])
    sys.exit()
class HoverLabel(tk.Label):
    def __init__(self, master, pil_image, *args, **kwargs):
        # pil_image: PIL Image (RGBA)
        self.pil_image_original = pil_image.convert("RGBA")
        self.animating = False
        self.anim_step = 0
        self.anim_dir = 1  # Für Ping-Pong Animation des Glows
        self.glow_pos = 0
        self.tk_image = ImageTk.PhotoImage(self.pil_image_original)
        super().__init__(master, image=self.tk_image, *args, **kwargs)
        self.bind("<Enter>", self.start_animation)
        self.bind("<Leave>", self.stop_animation)

    def start_animation(self, event=None):
        if not self.animating:
            self.animating = True
            self.anim_step = 0
            self.glow_pos = 0
            self.anim_dir = 1
            self.animate()

    def animate(self):
        if not self.animating:
            # Reset auf Originalbild, wenn Hover weg
            self.tk_image = ImageTk.PhotoImage(self.pil_image_original)
            self.config(image=self.tk_image)
            return

        # Helligkeit etwas erhöhen beim Hover
        enhancer = ImageEnhance.Brightness(self.pil_image_original)
        bright_img = enhancer.enhance(1.2)

        # Glow: Ein schmaler, halbtransparenter Weiß-Gradient, der sich bewegt
        glow_width = int(bright_img.width * 0.3)
        glow = Image.new("RGBA", bright_img.size, (0, 0, 0, 0))
        for x in range(glow_width):
            alpha = int(100 * (1 - abs(x - self.glow_pos) / glow_width))
            for y in range(bright_img.height):
                px = x + self.glow_pos
                if 0 <= px < bright_img.width:
                    glow.putpixel((px, y), (255, 255, 255, alpha))

        img_with_glow = Image.alpha_composite(bright_img, glow)

        self.tk_image = ImageTk.PhotoImage(img_with_glow)
        self.config(image=self.tk_image)

        # Glow wandert vor und zurück
        self.glow_pos += self.anim_dir * 5
        if self.glow_pos <= 0 or self.glow_pos + glow_width >= bright_img.width:
            self.anim_dir *= -1

        self.after(50, self.animate)

    def stop_animation(self, event=None):
        self.animating = False

class PyFlixApp:
    def __init__(self, root):
        self.root = root
        self.root.title("PyFlix - Netflix Clone")
        self.root.geometry("1200x750")
        self.root.configure(bg="#141414")
        self.current_frame = None
        self.film_base_path = os.getcwd()
        self.playing_audio = False
        self.font_bold = font.Font(family="Helvetica", size=14, weight="bold")
        self.font_regular = font.Font(family="Helvetica", size=11)

        # Für Hintergrundbild in Episode Menu
        self.background_label = None
        self.background_img_original = None

        self.show_loading_screen()

        # Filme im Hintergrund laden, danach Hauptmenu zeigen
        threading.Thread(target=self.load_films_and_show_menu, daemon=True).start()

    def show_loading_screen(self):
        self.clear_frame()
        self.current_frame = tk.Frame(self.root, bg="#141414")
        self.current_frame.pack(fill="both", expand=True)

        loading_label = tk.Label(self.current_frame, text="PyFlix lädt...", font=("Helvetica", 30, "bold"), fg="#E50914", bg="#141414")
        loading_label.pack(expand=True)

        # Einfache Puls-Animation
        def pulse(step=0):
            color_val = 200 + int(55 * (1 + (-1)**step) / 2)  # wechselt zwischen 200 und 255
            loading_label.config(fg=f"#E5{color_val:02X}14")
            self.root.after(500, lambda: pulse(1 - step))
        pulse()

    def load_films_and_show_menu(self):
        # Simulierte Ladezeit (entfernen, wenn du möchtest)
        time.sleep(2)

        # Nach dem Laden: Hauptmenü im MainThread anzeigen
        self.root.after(0, self.show_main_menu)

    def clear_frame(self):
        if self.current_frame:
            self.current_frame.destroy()
            self.current_frame = None

    def play_audio_loop(self, audio_path):
        if os.path.exists(audio_path):
            pygame.mixer.music.load(audio_path)
            pygame.mixer.music.play(loops=-1)
            self.playing_audio = True

    def stop_audio(self):
        pygame.mixer.music.stop()
        self.playing_audio = False

    def launch_vlc(self, video_path):
        self.stop_audio()
        subprocess.Popen([VLC_PATH, "--play-and-exit", video_path])

    def show_main_menu(self):
        self.stop_audio()
        self.clear_frame()
        self.current_frame = tk.Frame(self.root, bg="#141414")
        self.current_frame.pack(fill="both", expand=True)

        title = tk.Label(self.current_frame, text="🎬 Willkommen bei PyFlix",
                        font=("Helvetica", 28, "bold"), fg="white", bg="#141414")
        title.pack(pady=25)

        film_frame = tk.Frame(self.current_frame, bg="#141414")
        film_frame.pack(padx=20, pady=10, fill="both", expand=True)

        films = [f for f in os.listdir(self.film_base_path) if os.path.isdir(f)]
        col = 0
        row = 0

        for film in films:
            cover_path = os.path.join(film, "Cover", "cover.jpg")
            if not os.path.exists(cover_path):
                continue  # Kein Cover -> überspringen

            # Bild laden und Effekte anwenden (PIL Image)
            img = Image.open(cover_path).resize(FILM_COVER_SIZE)
            img = ImageEnhance.Brightness(img).enhance(1.2)
            img = ImageEnhance.Contrast(img).enhance(1.3)

            # Netflix-Glossy Effekt:
            gloss = Image.new("RGBA", img.size)
            for y in range(img.size[1]//3):
                alpha = int(120 * (1 - y/(img.size[1]//3)))
                for x in range(img.size[0]):
                    gloss.putpixel((x, y), (255, 255, 255, alpha))
            img = Image.alpha_composite(img.convert("RGBA"), gloss)

            # Übergabe an HoverLabel: PIL Image direkt, NICHT ImageTk.PhotoImage
            lbl = HoverLabel(film_frame, img, bg="#141414", cursor="hand2")
            lbl.grid(row=row, column=col, padx=20, pady=20)
            lbl.bind("<Button-1>", lambda e, name=film: self.show_dvd_menu(name))

            # Filmtitel drunter
            tk.Label(film_frame, text=film, font=self.font_bold, fg="white", bg="#141414").grid(row=row+1, column=col, pady=(0,20))

            col += 1
            if col > 3:
                col = 0
                row += 2  # Weil Titel auch 1 Reihe beansprucht

    def show_dvd_menu(self, film_name):
        self.clear_frame()
        self.current_frame = tk.Frame(self.root, bg="#1c1c1c")
        self.current_frame.pack(fill="both", expand=True)

        audio_path = os.path.join(film_name, "Audio", "soundtrack.mp3")
        self.play_audio_loop(audio_path)

        header = tk.Frame(self.current_frame, bg="#1c1c1c")
        header.pack(pady=20, fill="x")

        tk.Label(header, text=f"🎞 {film_name}", font=("Helvetica", 24, "bold"), fg="white", bg="#1c1c1c").pack(side="left", padx=20)
        tk.Button(header, text="🔙 Zurück", font=self.font_regular, command=self.show_main_menu).pack(side="right", padx=20)

        # Buttons für alle oder Episoden
        btn_frame = tk.Frame(self.current_frame, bg="#1c1c1c")
        btn_frame.pack(pady=10)

        tk.Button(btn_frame, text="▶ Alle abspielen", font=self.font_bold, bg="#e50914", fg="white",
                  activebackground="#f40612", padx=20, pady=10,
                  command=lambda: self.play_all_videos(film_name)).grid(row=0, column=0, padx=15)

        tk.Button(btn_frame, text="📺 Episoden-Auswahl", font=self.font_bold, bg="#221f1f", fg="white",
                  activebackground="#3a3939", padx=20, pady=10,
                  command=lambda: self.show_episode_menu(film_name)).grid(row=0, column=1, padx=15)

    def play_all_videos(self, film_name):
        self.stop_audio()
        folders = sorted([f for f in os.listdir(film_name) if f.lower().startswith("video")],
                        key=lambda x: int(''.join(filter(str.isdigit, x)) or 0))
        for folder in folders:
            folder_path = os.path.join(film_name, folder)
            videos = sorted([f for f in os.listdir(folder_path) if f.endswith(".mp4")])
            for file in videos:
                video_path = os.path.join(folder_path, file)
                # Hier warten wir, bis VLC schließt, bevor das nächste Video startet:
                subprocess.run([VLC_PATH, "--play-and-exit", video_path])

    def show_episode_menu(self, film_name):
        self.clear_frame()
        self.current_frame = tk.Frame(self.root, bg="#1c1c1c")
        self.current_frame.pack(fill="both", expand=True)

        # Hintergrundbild laden
        background_path = os.path.join(film_name, "Cover", "background.jpg")
        if os.path.exists(background_path):
            self.background_img_original = Image.open(background_path).convert("RGBA")
        else:
            self.background_img_original = None

        # Canvas als Hintergrund
        self.bg_canvas = tk.Canvas(self.current_frame, bg="#1c1c1c", highlightthickness=0)
        self.bg_canvas.pack(fill="both", expand=True)
        self.bg_canvas.bind("<Configure>", self.resize_background)

        # Frame mit Scrollbar auf Canvas
        self.scroll_frame = tk.Frame(self.bg_canvas, bg="#1c1c1c")

        self.canvas_window = self.bg_canvas.create_window((0, 0), window=self.scroll_frame, anchor="nw")

        scrollbar = tk.Scrollbar(self.current_frame, orient="vertical", command=self.bg_canvas.yview)
        scrollbar.pack(side="right", fill="y")

        self.bg_canvas.configure(yscrollcommand=scrollbar.set)

        self.scroll_frame.bind(
            "<Configure>",
            lambda e: self.bg_canvas.configure(scrollregion=self.bg_canvas.bbox("all"))
        )

        # Header oben über Canvas (damit immer sichtbar)
        header = tk.Frame(self.current_frame, bg="#1c1c1c")
        header.place(relx=0, rely=0, relwidth=1)
        tk.Label(header, text="📺 Episoden-Auswahl", font=("Helvetica", 24, "bold"), fg="white", bg="#1c1c1c").pack(side="left", padx=20, pady=10)
        tk.Button(header, text="🔙 Zurück", font=self.font_regular,
                  command=lambda: self.show_dvd_menu(film_name)).pack(side="right", padx=20, pady=10)

        folders = sorted([f for f in os.listdir(film_name) if f.lower().startswith("video")],
                         key=lambda x: int(''.join(filter(str.isdigit, x)) or 0))
        row = 1  # wegen Header
        col = 0

        thumb_dir = os.path.join(film_name, "thumbnails")
        os.makedirs(thumb_dir, exist_ok=True)

        for folder in folders:
            video_folder = os.path.join(film_name, folder)
            videos = sorted([v for v in os.listdir(video_folder) if v.endswith(".mp4")])
            ep_num = 1

            for video in videos:
                video_path = os.path.join(video_folder, video)
                thumb_path = os.path.join(thumb_dir, f"{folder}_{video}.jpg")

                # Thumbnail mit ffmpeg erstellen
                if not os.path.exists(thumb_path):
                    subprocess.run([
                        "ffmpeg", "-ss", THUMBNAIL_TIME, "-i", video_path,
                        "-frames:v", "1", "-q:v", "2", thumb_path
                    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

                # Bild laden und verkleinern
                if os.path.exists(thumb_path):
                    img = Image.open(thumb_path).resize(THUMBNAIL_SIZE)

                    # Übergabe an HoverLabel: PIL Image, nicht ImageTk.PhotoImage
                    lbl_img = HoverLabel(self.scroll_frame, img, bg="#222222", cursor="hand2")
                    lbl_img.grid(row=row, column=col, padx=15, pady=15)

                    # Episoden-Nummer
                    num_lbl = tk.Label(self.scroll_frame, text=f"Episode {ep_num}", fg="white", bg="#222222",
                                       font=self.font_bold)
                    num_lbl.grid(row=row+1, column=col, sticky="w", padx=15, pady=(0,5))

                    # Beschreibung aus JSON oder TXT laden
                    desc_text = "Keine Beschreibung vorhanden."
                    desc_path_json = os.path.join(video_folder, "info.json")
                    desc_path_txt = os.path.join(video_folder, "description.txt")
                    if os.path.exists(desc_path_json):
                        try:
                            with open(desc_path_json, "r", encoding="utf-8") as f:
                                data = json.load(f)
                                desc_text = data.get("description", desc_text)
                        except Exception:
                            pass
                    elif os.path.exists(desc_path_txt):
                        try:
                            with open(desc_path_txt, "r", encoding="utf-8") as f:
                                desc_text = f.read()
                        except Exception:
                            pass

                    desc_lbl = tk.Label(self.scroll_frame, text=desc_text, wraplength=THUMBNAIL_SIZE[0],
                                        justify="left", fg="white", bg="#222222", font=self.font_regular)
                    desc_lbl.grid(row=row+2, column=col, sticky="w", padx=15, pady=(0,20))

                    # Klick-Event zum Abspielen der Episode
                    lbl_img.bind("<Button-1>", lambda e, path=video_path: self.launch_vlc(path))

                    col += 1
                    if col >= 4:
                        col = 0
                        row += 3
                    ep_num += 1

    def resize_background(self, event):
        if self.background_img_original:
            w, h = event.width, event.height
            resized = self.background_img_original.resize((w, h), Image.LANCZOS)
            self.bg_image_tk = ImageTk.PhotoImage(resized)
            # Bild als Hintergrund auf Canvas zeichnen
            self.bg_canvas.create_image(0, 0, image=self.bg_image_tk, anchor="nw")
        self.bg_canvas.config(scrollregion=self.bg_canvas.bbox("all"))

def main():
    root = tk.Tk()
    app = PyFlixApp(root)
    root.mainloop()

if __name__ == "__main__":
     if check_for_update():
        # Update wurde gestartet, beende das Programm
        sys.exit()

        # Rest deines Programms hier starten, z.B.:
        import tkinter as tk
        root = tk.Tk()
        # ... Dein PyFlixApp starten
        root.mainloop()
