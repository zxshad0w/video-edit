import os
import time
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from PIL import Image, ImageTk
from moviepy import VideoFileClip, AudioFileClip, vfx


class PyCutProApp:

    def __init__(self, root):
        self.root = root
        self.root.title("PyCut Pro — Professional Desktop Edition")

        # Требование 3: Ограничение размеров окна (минимальные границы)
        self.root.geometry("1100x750")
        self.root.minsize(1024, 700)
        self.root.configure(bg="#121214")

        # Ядро проекта
        self.video_clip = None  # Исходный чистый клип
        self.modified_clip = None  # Клип со всей цепочкой изменений
        self.audio_clip = None  # Сторонняя аудиодорожка
        self.mute_original = False

        # Движок плеера
        self.is_playing = False
        self.current_time = 0.0
        self.last_update_time = 0.0

        self.setup_styles()
        self.build_layout()

        # Требование 3: При изменении размеров окна перерисовываем кадр без искажений
        self.video_canvas.bind("<Configure>", self.on_canvas_resize)

    def setup_styles(self):
        """Интерфейсные стили под CapCut UI"""
        self.style = ttk.Style()
        self.style.theme_use("clam")

        self.style.configure(
            "CapCut.TButton",
            background="#252529",
            foreground="white",
            bordercolor="#121214",
            font=("Arial", 10, "bold"),
            padding=8,
        )
        self.style.map(
            "CapCut.TButton",
            background=[("active", "#3a3a40")],
            foreground=[("active", "#00febe")],
        )

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

        # Главный разделитель (Инструменты / Плеер)
        top_paned = tk.PanedWindow(
            self.root, orient="horizontal", bg="#121214", bd=0, sashwidth=4
        )
        top_paned.pack(fill="both", expand=True, padx=10, pady=5)

        # ==========================================
        # ЛЕВАЯ ПАНЕЛЬ: УПРАВЛЕНИЕ И НАСТРОЙКИ
        # ==========================================
        self.left_panel = tk.LabelFrame(
            top_paned,
            text=" Инструменты монтажа ",
            bg="#18181c",
            fg="white",
            font=("Arial", 10, "bold"),
            bd=1,
        )
        top_paned.add(self.left_panel, width=360)

        scroll_frame = tk.Frame(self.left_panel, bg="#18181c", padx=10, pady=10)
        scroll_frame.pack(fill="both", expand=True)

        # Блок 1: Импорт ресурсов
        import_frame = tk.LabelFrame(
            scroll_frame,
            text=" Импорт файлов ",
            bg="#202024",
            fg="#a0a0a5",
            pady=8,
            padx=5,
        )
        import_frame.pack(fill="x", pady=5)

        ttk.Button(
            import_frame,
            text="📁 Добавить Видео (.mp4)",
            style="CapCut.TButton",
            command=self.import_video,
        ).pack(fill="x", pady=4)
        ttk.Button(
            import_frame,
            text="🎵 Добавить Аудио (.mp3/.wav)",
            style="CapCut.TButton",
            command=self.import_audio,
        ).pack(fill="x", pady=4)

        # Блок 2: Настройки Трека (Громкость и Скорость)
        track_frame = tk.LabelFrame(
            scroll_frame,
            text=" Модификация дорожек ",
            bg="#202024",
            fg="#a0a0a5",
            pady=10,
            padx=8,
        )
        track_frame.pack(fill="x", pady=10)

        # Требование 1: Ползунок громкости
        tk.Label(
            track_frame,
            text="🎚 Громкость звука:",
            bg="#202024",
            fg="white",
            font=("Arial", 9, "bold"),
        ).pack(anchor="w")
        self.volume_slider = tk.Scale(
            track_frame,
            from_=0,
            to=200,
            orient="horizontal",
            bg="#252529",
            fg="#00febe",
            troughcolor="#141416",
            highlightthickness=0,
            font=("Consolas", 9),
            command=self.on_param_changed,
        )
        self.volume_slider.set(100)
        self.volume_slider.pack(fill="x", pady=(2, 10))

        self.btn_mute = ttk.Button(
            track_frame,
            text=" Mute (Полная тишина)",
            style="CapCut.TButton",
            command=self.toggle_mute,
        )
        self.btn_mute.pack(fill="x", pady=(0, 10))

        # Требование 2: Изменение скорости видео и звука
        tk.Label(
            track_frame,
            text="⚡ Скорость (Видео + Аудио):",
            bg="#202024",
            fg="white",
            font=("Arial", 9, "bold"),
        ).pack(anchor="w")
        self.speed_combo = ttk.Combobox(
            track_frame,
            values=["0.5", "0.75", "1.0", "1.25", "1.5", "2.0"],
            state="readonly",
        )
        self.speed_combo.set("1.0")
        self.speed_combo.pack(fill="x", pady=4)
        self.speed_combo.bind("<<ComboboxSelected>>", self.on_param_changed)

        # Блок 3: Требование 5 - Выбор качества экспорта
        export_cfg_frame = tk.LabelFrame(
            scroll_frame,
            text=" Конфигурация экспорта ",
            bg="#202024",
            fg="#a0a0a5",
            pady=10,
            padx=8,
        )
        export_cfg_frame.pack(fill="x", pady=5)

        tk.Label(
            export_cfg_frame,
            text="Разрешение сохранения:",
            bg="#202024",
            fg="white",
        ).pack(anchor="w")
        self.quality_combo = ttk.Combobox(
            export_cfg_frame,
            values=["Исходное", "1080p (Full HD)", "720p (HD)", "480p (SD)"],
            state="readonly",
        )
        self.quality_combo.set("Исходное")
        self.quality_combo.pack(fill="x", pady=4)

        # Технический статус проекта
        self.lbl_media_info = tk.Label(
            scroll_frame,
            text="Проект ожидает файлы...",
            bg="#18181c",
            fg="#66666a",
            justify="left",
            font=("Arial", 9, "italic"),
        )
        self.lbl_media_info.pack(fill="x", side="bottom", pady=10)

        # ==========================================
        # ПРАВАЯ ПАНЕЛЬ: ЖИВОЙ ПЛЕЕР ПРЕДПРОСМОТРА
        # ==========================================
        self.player_panel = tk.Frame(top_paned, bg="#18181c")
        top_paned.add(self.player_panel, width=720)

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

        self.lbl_time_digital = tk.Label(
            player_ctrls,
            text="00:00.0 / 00:00.0",
            bg="#18181c",
            fg="white",
            font=("Consolas", 11),
        )
        self.lbl_time_digital.pack(side="right", padx=15)

        # ==========================================
        # НИЖНЯЯ ПАНЕЛЬ: ИНТЕРАКТИВНЫЙ ТАЙМЛАЙН
        # ==========================================
        bottom_panel = tk.Frame(self.root, bg="#18181c", height=180, bd=1)
        bottom_panel.pack(fill="x", side="bottom", padx=10, pady=10)

        timeline_header = tk.Frame(bottom_panel, bg="#202024", height=40)
        timeline_header.pack(fill="x")

        tk.Label(
            timeline_header,
            text=" 🎞 Таймлайн трека (Скраббинг)",
            bg="#202024",
            fg="white",
            font=("Arial", 10, "bold"),
        ).pack(side="left", padx=10, pady=5)

        ttk.Button(
            timeline_header,
            text="🚀 Собрать и Скачать Видео",
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
    # ЯДРО ОБРАБОТКИ ЭФФЕКТОВ И СЛОЕВ
    # ==========================================

    def apply_modifications(self):
        """Пересчитывает стек изменений без разрушения исходника"""
        if not self.video_clip:
            return

        # Начинаем с чистого листа
        clip = self.video_clip

        # 1. Применяем логику звука (родной или наложенный)
        if self.mute_original:
            clip = clip.without_audio()
        elif self.audio_clip:
            clip = clip.with_audio(self.audio_clip)

        # Требование 1: Контроль уровня громкости
        if clip.audio is not None:
            vol_factor = self.volume_slider.get() / 100.0
            clip = clip.with_volume_scaled(vol_factor)

        # Требование 2: Синхронное изменение скорости видео и звука
        speed_factor = float(self.speed_combo.get())
        if speed_factor != 1.0:
            clip = clip.with_speed_scaled(speed_factor)

        self.modified_clip = clip

        # Перенастраиваем шкалу времени под новую длительность
        self.time_slider.config(from_=0, to=self.modified_clip.duration)
        if self.current_time > self.modified_clip.duration:
            self.current_time = self.modified_clip.duration
            self.time_slider.set(self.current_time)

    def on_param_changed(self, *args):
        """Срабатывает при любом изменении ползунков/комбобоксов настроек"""
        if self.video_clip:
            self.apply_modifications()
            self.show_frame_at_time(self.current_time)

    def import_video(self):
        """Загрузка исходного видеофайла"""
        file_path = filedialog.askopenfilename(
            filetypes=[("Video Files", "*.mp4 *.avi *.mov *.mkv")]
        )
        if not file_path:
            return

        self.pause_video()
        self.video_clip = VideoFileClip(file_path)

        # Сбрасываем ползунки на дефолт при новом файле
        self.volume_slider.set(100)
        self.speed_combo.set("1.0")
        self.mute_original = False
        self.btn_mute.config(text=" Mute (Полная тишина)")

        self.apply_modifications()

        self.time_slider.set(0)
        self.current_time = 0.0

        filename = os.path.basename(file_path)
        self.lbl_media_info.config(
            text=f"Файл: {filename}\nДлительность: {self.video_clip.duration:.2f} сек\nРазмер: {self.video_clip.size[0]}x{self.video_clip.size[1]}",
            fg="#00febe",
        )

        self.show_frame_at_time(0)

    def import_audio(self):
        """Наложение фоновой музыки взамен или вместе"""
        if not self.video_clip:
            return messagebox.showerror("Внимание", "Сначала импортируйте видео!")

        file_path = filedialog.askopenfilename(
            filetypes=[("Audio Files", "*.mp3 *.wav")]
        )
        if not file_path:
            return

        try:
            self.audio_clip = AudioFileClip(file_path)
            # Подгоняем длину музыки под длину исходного клипа
            if self.audio_clip.duration > self.video_clip.duration:
                self.audio_clip = self.audio_clip.subclipped(
                    0, self.video_clip.duration
                )

            self.apply_modifications()
            messagebox.showinfo("Звук", "Новая аудиодорожка успешно внедрена!")
        except Exception as e:
            messagebox.showerror("Ошибка аудио", f"Не удалось прочесть трек: {e}")

    def toggle_mute(self):
        """Полная тишина клипа"""
        if not self.video_clip:
            return

        self.mute_original = not self.mute_original
        if self.mute_original:
            self.btn_mute.config(text="🔊 Вернуть звук оригинального клипа")
        else:
            self.btn_mute.config(text=" Mute (Полная тишина)")

        self.apply_modifications()
        self.show_frame_at_time(self.current_time)

    # ==========================================
    # РАБОТА С ЭКРАНОМ (PREVIEW ENGINE)
    # ==========================================

    def show_frame_at_time(self, t):
        """Извлечение и правильный рендеринг кадра на Canvas"""
        if not self.modified_clip:
            return

        if t < 0:
            t = 0
        if t > self.modified_clip.duration:
            t = self.modified_clip.duration

        frame_array = self.modified_clip.get_frame(t)
        img = Image.fromarray(frame_array)

        # Динамически берем геометрию холста
        canvas_width = self.video_canvas.winfo_width()
        canvas_height = self.video_canvas.winfo_height()

        if canvas_width < 10 or canvas_height < 10:
            canvas_width, canvas_height = 700, 350

        # Требование 3: Масштабируем без искажений (объема) через thumbnail с LANCZOS
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
        """Перерисовывает кадр при изменении размеров окна пользователем"""
        if self.modified_clip and not self.is_playing:
            self.show_frame_at_time(self.current_time)

    def on_slider_scrub(self, value):
        """Скраббинг видео вручную"""
        if self.modified_clip and not self.is_playing:
            self.current_time = float(value)
            self.show_frame_at_time(self.current_time)

    # ==========================================
    # ДВИЖОК ОБНОВЛЕНИЯ ПОТОКА (100 HZ)
    # ==========================================

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
        """Высокогерцовый игровой цикл плеера"""
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

        # Требование 4: Задержка 10 миллисекунд дает частоту опроса в 100 Гц
        self.root.after(10, self.update_player_loop)

    # ==========================================
    # СБОРКА И ЭКСПОРТ (CUSTOM QUALITY)
    # ==========================================

    def export_project(self):
        """Сборка фильма с учетом выбранного разрешения"""
        if not self.modified_clip:
            return messagebox.showerror("Экспорт", "Нет данных для рендеринга!")

        save_path = filedialog.asksaveasfilename(
            defaultextension=".mp4",
            filetypes=[("MP4 Video", "*.mp4")],
            title="Экспорт смонтированного видео",
        )

        if not save_path:
            return

        self.pause_video()

        # Подготовка кастомного разрешения (Требование 5)
        quality = self.quality_combo.get()
        export_clip = self.modified_clip

        if quality == "1080p (Full HD)":
            export_clip = export_clip.resized(height=1080)
        elif quality == "720p (HD)":
            export_clip = export_clip.resized(height=720)
        elif quality == "480p (SD)":
            export_clip = export_clip.resized(height=480)

        # Окно рендеринга
        info_window = tk.Toplevel(self.root)
        info_window.title("Рендеринг...")
        info_window.geometry("420x130")
        info_window.configure(bg="#18181c")
        info_window.transient(self.root)
        info_window.grab_set()

        tk.Label(
            info_window,
            text=f"🎬 Идет компиляция видео в качестве: {quality}\nПожалуйста, подождите завершения процесса.",
            bg="#18181c",
            fg="#00febe",
            font=("Arial", 10, "bold"),
            pady=25,
        ).pack()
        self.root.update()

        try:
            # Рендеринг файла
            export_clip.write_videofile(
                save_path,
                codec="libx264",
                audio_codec="aac",
                fps=24,
                threads=4,
            )
            info_window.destroy()
            messagebox.showinfo(
                "Экспорт завершен", f"Файл успешно скачан:\n{save_path}"
            )
        except Exception as e:
            info_window.destroy()
            messagebox.showerror("Ошибка рендеринга", f"Сборка сорвалась: {e}")


if __name__ == "__main__":
    root = tk.Tk()
    app = PyCutProApp(root)
    root.update()
    root.mainloop()
