import os
import time
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from PIL import Image, ImageTk
from moviepy import VideoFileClip, AudioFileClip, concatenate_videoclips, vfx


class PyCutProApp:

    def __init__(self, root):
        self.root = root
        self.root.title("PyCut Pro — Фикс Форматов и Стабильный Экспорт")

        # Ограничения и геометрия окна
        self.root.geometry("1150x800")
        self.root.minsize(1050, 720)
        self.root.configure(bg="#121214")

        # Ядро нелинейного монтажа
        self.video_clip = None
        self.clip_chain = []
        self.modified_clip = None
        self.audio_clip = None
        self.mute_original = False

        # Движок плеера (100 Гц)
        self.is_playing = False
        self.current_time = 0.0
        self.last_update_time = 0.0

        self.setup_styles()
        self.build_layout()

        self.video_canvas.bind("<Configure>", self.on_canvas_resize)

    def setup_styles(self):
        """Интерфейсные стили CapCut UI"""
        self.style = ttk.Style()
        self.style.theme_use("clam")

        self.style.configure(
            "CapCut.TButton",
            background="#252529",
            foreground="white",
            bordercolor="#121214",
            font=("Arial", 10, "bold"),
            padding=7,
        )
        self.style.map(
            "CapCut.TButton",
            background=[("active", "#3a3a40")],
            foreground=[("active", "#00febe")],
        )

        self.style.configure(
            "Cut.TButton",
            background="#cc3333",
            foreground="white",
            bordercolor="#121214",
            font=("Arial", 10, "bold"),
            padding=7,
        )
        self.style.map("Cut.TButton", background=[("active", "#ff4444")])

        self.style.configure(
            "Export.TButton",
            background="#00febe",
            foreground="black",
            bordercolor="#121214",
            font=("Arial", 10, "bold"),
            padding=10,
        )
        self.style.map("Export.TButton", background=[("active", "#00dfa6")])

    def build_layout(self):
        """Построение сетки интерфейса"""
        top_paned = tk.PanedWindow(
            self.root, orient="horizontal", bg="#121214", bd=0, sashwidth=4
        )
        top_paned.pack(fill="both", expand=True, padx=10, pady=5)

        # ЛЕВАЯ ПАНЕЛЬ
        self.left_panel = tk.LabelFrame(
            top_paned,
            text=" Панель управления ",
            bg="#18181c",
            fg="white",
            font=("Arial", 10, "bold"),
            bd=1,
        )
        top_paned.add(self.left_panel, width=380)

        scroll_frame = tk.Frame(self.left_panel, bg="#18181c", padx=10, pady=10)
        scroll_frame.pack(fill="both", expand=True)

        # 1. Импорт
        import_frame = tk.LabelFrame(
            scroll_frame,
            text=" 1. Импорт исходников ",
            bg="#202024",
            fg="#a0a0a5",
            pady=6,
            padx=5,
        )
        import_frame.pack(fill="x", pady=4)

        ttk.Button(
            import_frame,
            text="📁 Импортировать Видео (.mp4)",
            style="CapCut.TButton",
            command=self.import_video,
        ).pack(fill="x", pady=3)
        ttk.Button(
            import_frame,
            text="🎵 Наложить фоновую Музыку",
            style="CapCut.TButton",
            command=self.import_audio,
        ).pack(fill="x", pady=3)

        # 2. Форматы (ИСПРАВЛЕНО)
        ratio_frame = tk.LabelFrame(
            scroll_frame,
            text=" 2. Соотношение сторон (Формат) ",
            bg="#202024",
            fg="#a0a0a5",
            pady=8,
            padx=8,
        )
        ratio_frame.pack(fill="x", pady=6)

        self.ratio_combo = ttk.Combobox(
            ratio_frame,
            values=[
                "Original",
                "16:9 (Кино/YouTube)",
                "4:3 (Квадрат)",
                "9:16 (TikTok/Shorts)",
            ],
            state="readonly",
        )
        self.ratio_combo.set("Original")
        self.ratio_combo.pack(fill="x", pady=2)
        self.ratio_combo.bind("<<ComboboxSelected>>", self.on_param_changed)

        # 3. Аудиомикшер
        audio_frame = tk.LabelFrame(
            scroll_frame,
            text=" 3. Аудиомикшер ",
            bg="#202024",
            fg="#a0a0a5",
            pady=8,
            padx=8,
        )
        audio_frame.pack(fill="x", pady=6)

        tk.Label(
            audio_frame, text="Громкость микса:", bg="#202024", fg="white"
        ).pack(anchor="w")
        self.volume_slider = tk.Scale(
            audio_frame,
            from_=0,
            to=200,
            orient="horizontal",
            bg="#252529",
            fg="#00febe",
            troughcolor="#141416",
            highlightthickness=0,
            command=self.on_param_changed,
        )
        self.volume_slider.set(100)
        self.volume_slider.pack(fill="x", pady=(2, 6))

        self.btn_mute = ttk.Button(
            audio_frame,
            text="🔇 Заглушить всё видео",
            style="CapCut.TButton",
            command=self.toggle_mute,
        )
        self.btn_mute.pack(fill="x", pady=2)

        ttk.Button(
            audio_frame,
            text="❌ Удалить мою музыку (Вернуть оригинал)",
            style="CapCut.TButton",
            command=self.restore_original_audio,
        ).pack(fill="x", pady=2)

        # 4. Скорость
        speed_frame = tk.LabelFrame(
            scroll_frame,
            text=" 4. Управление скоростью ",
            bg="#202024",
            fg="#a0a0a5",
            pady=8,
            padx=8,
        )
        speed_frame.pack(fill="x", pady=6)

        self.speed_combo = ttk.Combobox(
            speed_frame,
            values=["0.5", "0.75", "1.0", "1.25", "1.5", "2.0"],
            state="readonly",
        )
        self.speed_combo.set("1.0")
        self.speed_combo.pack(fill="x", pady=2)
        self.speed_combo.bind("<<ComboboxSelected>>", self.on_param_changed)

        # 5. Экспорт
        export_cfg_frame = tk.LabelFrame(
            scroll_frame,
            text=" 5. Настройка качества сохранения ",
            bg="#202024",
            fg="#a0a0a5",
            pady=8,
            padx=8,
        )
        export_cfg_frame.pack(fill="x", pady=6)

        self.quality_combo = ttk.Combobox(
            export_cfg_frame,
            values=["Исходное", "1080p (Full HD)", "720p (HD)", "480p (SD)"],
            state="readonly",
        )
        self.quality_combo.set("Исходное")
        self.quality_combo.pack(fill="x", pady=2)

        self.lbl_media_info = tk.Label(
            scroll_frame,
            text="Фрагментов в склейке: 0",
            bg="#18181c",
            fg="#88888c",
            justify="left",
            font=("Arial", 9, "bold"),
        )
        self.lbl_media_info.pack(fill="x", side="bottom", pady=5)

        # ПРАВАЯ ПАНЕЛЬ ПЛЕЕРА
        self.player_panel = tk.Frame(top_paned, bg="#18181c")
        top_paned.add(self.player_panel, width=730)

        self.video_canvas = tk.Canvas(
            self.player_panel, bg="black", highlightthickness=0
        )
        self.video_canvas.pack(fill="both", expand=True, padx=10, pady=10)

        player_ctrls = tk.Frame(self.player_panel, bg="#18181c")
        player_ctrls.pack(fill="x", pady=5)

        self.btn_play = ttk.Button(
            player_ctrls,
            text="▶ PLAY",
            style="CapCut.TButton",
            width=10,
            command=self.play_video,
        )
        self.btn_play.pack(side="left", padx=10)

        self.btn_pause = ttk.Button(
            player_ctrls,
            text="⏸ PAUSE",
            style="CapCut.TButton",
            width=10,
            command=self.pause_video,
        )
        self.btn_pause.pack(side="left")

        self.btn_cut = ttk.Button(
            player_ctrls,
            text="✂ РАЗРЕЗАТЬ фрагмент",
            style="Cut.TButton",
            command=self.split_active_clip,
        )
        self.btn_cut.pack(side="left", padx=20)

        self.lbl_time_digital = tk.Label(
            player_ctrls,
            text="00:00.00 / 00:00.00",
            bg="#18181c",
            fg="white",
            font=("Consolas", 11),
        )
        self.lbl_time_digital.pack(side="right", padx=15)

        # ТАЙМЛАЙН
        bottom_panel = tk.Frame(self.root, bg="#18181c", height=160, bd=1)
        bottom_panel.pack(fill="x", side="bottom", padx=10, pady=10)

        timeline_header = tk.Frame(bottom_panel, bg="#202024", height=40)
        timeline_header.pack(fill="x")

        tk.Label(
            timeline_header,
            text=" 🎞 Интерактивная монтажная дорожка (Скраббинг)",
            bg="#202024",
            fg="white",
            font=("Arial", 10, "bold"),
        ).pack(side="left", padx=10, pady=5)

        ttk.Button(
            timeline_header,
            text="🚀 Собрать и Скачать Фильм",
            style="Export.TButton",
            command=self.export_project,
        ).pack(side="right", padx=10, pady=2)

        timeline_body = tk.Frame(bottom_panel, bg="#141416", pady=15, padx=15)
        timeline_body.pack(fill="both", expand=True)

        self.time_slider = tk.Scale(
            timeline_body,
            from_=0,
            to=100,
            orient="horizontal",
            resolution=0.01,
            bg="#252529",
            fg="white",
            troughcolor="#1a1a1e",
            highlightthickness=0,
            command=self.on_slider_scrub,
        )
        self.time_slider.pack(fill="x", expand=True)

    # ==========================================
    # ЯДРО ОБРАБОТКИ И КРОПА (ИСПРАВЛЕНО)
    # ==========================================

    def apply_modifications(self):
        """Собирает фрагменты и безопасно кадрирует их по координатам пикселей"""
        if not self.clip_chain:
            return

        try:
            if len(self.clip_chain) > 1:
                base_clip = concatenate_videoclips(
                    self.clip_chain, method="compose"
                )
            else:
                base_clip = self.clip_chain[0]

            # ИСПРАВЛЕНО: Математика кропа переведена на чистые x1, y1, x2, y2
            ratio_val = self.ratio_combo.get()
            if ratio_val and ratio_val != "Original":
                if "16:9" in ratio_val:
                    target_ratio = 16.0 / 9.0
                elif "4:3" in ratio_val:
                    target_ratio = 4.0 / 3.0
                elif "9:16" in ratio_val:
                    target_ratio = 9.0 / 16.0
                else:
                    target_ratio = None

                if target_ratio:
                    curr_w, curr_h = base_clip.w, base_clip.h
                    curr_ratio = curr_w / curr_h

                    if curr_ratio > target_ratio:
                        # Видео шире чем надо -> режем бока
                        new_w = int(curr_h * target_ratio)
                        new_w = new_w - (new_w % 2)
                        x1 = (curr_w - new_w) // 2
                        x2 = x1 + new_w
                        y1 = 0
                        y2 = curr_h
                    else:
                        # Видео выше чем надо -> режем верх и низ
                        new_h = int(curr_w / target_ratio)
                        new_h = new_h - (new_h % 2)
                        x1 = 0
                        x2 = curr_w
                        y1 = (curr_h - new_h) // 2
                        y2 = y1 + new_h

                    # Кроп, совместимый со ВСЕМИ версиями MoviePy (1.x и 2.x)
                    if hasattr(base_clip, "cropped"):
                        base_clip = base_clip.cropped(
                            x1=x1, y1=y1, x2=x2, y2=y2
                        )
                    else:
                        base_clip = base_clip.crop(x1=x1, y1=y1, x2=x2, y2=y2)

            # Настройка звука
            if self.mute_original:
                base_clip = base_clip.without_audio()
            elif self.audio_clip:
                base_clip = base_clip.with_audio(self.audio_clip)

            if base_clip.audio is not None:
                vol = self.volume_slider.get() / 100.0
                base_clip = base_clip.with_volume_scaled(vol)

            # Скорость
            speed_factor = float(self.speed_combo.get())
            if speed_factor != 1.0:
                base_clip = base_clip.with_speed_scaled(speed_factor)

            self.modified_clip = base_clip

            self.time_slider.config(from_=0, to=self.modified_clip.duration)
            if self.current_time > self.modified_clip.duration:
                self.current_time = self.modified_clip.duration
                self.time_slider.set(self.current_time)

            self.lbl_media_info.config(
                text=f"Фрагментов в склейке: {len(self.clip_chain)} | Общая длина: {self.modified_clip.duration:.2f} сек",
                fg="#00febe",
            )

        except Exception as e:
            print(f"Ошибка сборки проекта: {e}")

    def split_active_clip(self):
        if not self.clip_chain or not self.modified_clip:
            return messagebox.showwarning("Нарезка", "Загрузите видео!")

        t = self.current_time
        accumulated_time = 0.0

        for idx, clip in enumerate(self.clip_chain):
            clip_duration = clip.duration
            if accumulated_time <= t <= (accumulated_time + clip_duration + 0.01):
                local_t = t - accumulated_time

                if local_t <= 0.05 or local_t >= (clip_duration - 0.05):
                    messagebox.showwarning(
                        "Нарезка", "Нельзя резать на краях фрагментов!"
                    )
                    return

                part_a = clip.subclipped(0, local_t)
                part_b = clip.subclipped(local_t, clip.duration)

                self.clip_chain[idx] = part_a
                self.clip_chain.insert(idx + 1, part_b)

                self.pause_video()
                self.apply_modifications()
                self.show_frame_at_time(self.current_time)
                messagebox.showinfo(
                    "Нарезка", f"Разрезано в точке {t:.2f} сек!"
                )
                return
            accumulated_time += clip_duration

    def restore_original_audio(self):
        if not self.video_clip:
            return
        self.audio_clip = None
        self.apply_modifications()
        self.show_frame_at_time(self.current_time)
        messagebox.showinfo("Аудио", "Родной трек восстановлен!")

    # ==========================================
    # ИМПОРТ И СЛУШАТЕЛИ ПАНЕЛИ
    # ==========================================

    def import_video(self):
        file_path = filedialog.askopenfilename(
            filetypes=[("Video Files", "*.mp4 *.avi *.mov *.mkv")]
        )
        if not file_path:
            return

        self.pause_video()
        self.video_clip = VideoFileClip(file_path)
        self.clip_chain = [self.video_clip]

        self.volume_slider.set(100)
        self.speed_combo.set("1.0")
        self.ratio_combo.set("Original")
        self.mute_original = False

        self.apply_modifications()
        self.time_slider.set(0)
        self.current_time = 0.0
        self.show_frame_at_time(0)

    def import_audio(self):
        if not self.video_clip:
            return messagebox.showerror("Ошибка", "Сначала импортируйте видео!")
        file_path = filedialog.askopenfilename(
            filetypes=[("Audio Files", "*.mp3 *.wav")]
        )
        if not file_path:
            return
        try:
            self.audio_clip = AudioFileClip(file_path)
            if self.audio_clip.duration > self.modified_clip.duration:
                self.audio_clip = self.audio_clip.subclipped(
                    0, self.modified_clip.duration
                )
            self.apply_modifications()
            messagebox.showinfo("Звук", "Музыка добавлена!")
        except Exception as e:
            messagebox.showerror("Ошибка аудио", str(e))

    def toggle_mute(self):
        if not self.video_clip:
            return
        self.mute_original = not self.mute_original
        self.btn_mute.config(
            text="🔊 Вернуть аудио" if self.mute_original else "🔇 Заглушить всё видео"
        )
        self.apply_modifications()
        self.show_frame_at_time(self.current_time)

    def on_param_changed(self, *args):
        if self.video_clip:
            self.apply_modifications()
            self.show_frame_at_time(self.current_time)

    # ==========================================
    # ИСПРАВЛЕННЫЙ PREVIEW ENGINE
    # ==========================================

    def show_frame_at_time(self, t):
        if not self.modified_clip:
            return

        if t < 0:
            t = 0
        if t > self.modified_clip.duration:
            t = self.modified_clip.duration

        frame_array = self.modified_clip.get_frame(t)
        img = Image.fromarray(frame_array)

        canvas_width = self.video_canvas.winfo_width()
        canvas_height = self.video_canvas.winfo_height()

        # ИСПРАВЛЕНО: Безопасный порог (100px), защищающий плеер от схлопывания при инициализации «Оригинала»
        if canvas_width < 100 or canvas_height < 100:
            canvas_width, canvas_height = 730, 410

        img.thumbnail((canvas_width, canvas_height), Image.Resampling.LANCZOS)
        self.tk_image = ImageTk.PhotoImage(img)

        self.video_canvas.delete("all")
        self.video_canvas.create_image(
            canvas_width // 2,
            canvas_height // 2,
            anchor="center",
            image=self.tk_image,
        )
        self.lbl_time_digital.config(
            text=f"{t:.2f}s / {self.modified_clip.duration:.2f}s"
        )

    def on_canvas_resize(self, event):
        if self.modified_clip and not self.is_playing:
            self.show_frame_at_time(self.current_time)

    def on_slider_scrub(self, value):
        if self.modified_clip and not self.is_playing:
            self.current_time = float(value)
            self.show_frame_at_time(self.current_time)

    def play_video(self):
        if not self.modified_clip:
            return
        if not self.is_playing:
            self.is_playing = True
            self.last_update_time = time.time()
            self.update_player_loop()

    def pause_video(self):
        self.is_playing = False

    def update_player_loop(self):
        if not self.is_playing or not self.modified_clip:
            return

        now = time.time()
        delta = now - self.last_update_time
        self.last_update_time = now

        self.current_time += delta

        if self.current_time >= self.modified_clip.duration:
            self.current_time = self.modified_clip.duration
            self.is_playing = False
            self.time_slider.set(self.current_time)
            self.show_frame_at_time(self.current_time)
            return

        self.time_slider.set(self.current_time)
        self.show_frame_at_time(self.current_time)
        self.root.after(10, self.update_player_loop)

    # ==========================================
    # НАДЕЖНЫЙ ЭКСПОРТ (БЕЗ ТИПОВЫХ ОШИБОК РАЗМЕРОВ)
    # ==========================================

    def export_project(self):
        if not self.modified_clip:
            return messagebox.showerror("Экспорт", "Нечего компилировать!")

        save_path = filedialog.asksaveasfilename(
            defaultextension=".mp4",
            filetypes=[("MP4 Video", "*.mp4")],
            title="Сохранить смонтированное видео",
        )
        if not save_path:
            return

        self.pause_video()

        quality = self.quality_combo.get()
        export_clip = self.modified_clip

        # Безопасный ресайз через width/height под MoviePy 2.0+
        if "1080p" in quality:
            h = 1080
            w = int(export_clip.w * (h / export_clip.h))
            w = w - (w % 2)
            export_clip = export_clip.resized(width=w, height=h)
        elif "720p" in quality:
            h = 720
            w = int(export_clip.w * (h / export_clip.h))
            w = w - (w % 2)
            export_clip = export_clip.resized(width=w, height=h)
        elif "480p" in quality:
            h = 480
            w = int(export_clip.w * (h / export_clip.h))
            w = w - (w % 2)
            export_clip = export_clip.resized(width=w, height=h)
        else:
            # Страховка для профиля "Исходное": если у оригинального видео нечетные стороны,
            # FFMPEG упадет. Принудительно делаем их четными.
            if export_clip.w % 2 != 0 or export_clip.h % 2 != 0:
                w = export_clip.w - (export_clip.w % 2)
                h = export_clip.h - (export_clip.h % 2)
                export_clip = export_clip.resized(width=w, height=h)

        info_window = tk.Toplevel(self.root)
        info_window.title("Экспорт...")
        info_window.geometry("420x130")
        info_window.configure(bg="#18181c")
        info_window.transient(self.root)
        info_window.grab_set()

        tk.Label(
            info_window,
            text=f"🎬 Идет компиляция фильма...\nПрофиль: {quality}\nПожалуйста, подождите.",
            bg="#18181c",
            fg="#00febe",
            font=("Arial", 10, "bold"),
            pady=25,
        ).pack()
        self.root.update()

        try:
            export_clip.write_videofile(
                save_path,
                codec="libx264",
                audio_codec="aac",
                fps=24,
                threads=4,
            )
            info_window.destroy()
            messagebox.showinfo(
                "Готово!", f"Видео успешно сохранено:\n{save_path}"
            )
        except Exception as e:
            info_window.destroy()
            messagebox.showerror("Ошибка FFMPEG", f"Ошибка рендеринга: {str(e)}")


if __name__ == "__main__":
    root = tk.Tk()
    app = PyCutProApp(root)
    root.update()
    root.mainloop()
