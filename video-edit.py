import os
import time
import uuid
import tkinter as tk
from tkinter import filedialog, messagebox, ttk, colorchooser
from PIL import Image, ImageTk, ImageDraw, ImageFont
import pygame

# Безопасный импорт компонентов MoviePy для версий 1.x и 2.0+
try:
    from moviepy import VideoFileClip, AudioFileClip, concatenate_videoclips, CompositeVideoClip, ImageClip
except ImportError:
    # noinspection PyUnresolvedReferences
    from moviepy.editor import VideoFileClip, AudioFileClip, concatenate_videoclips, CompositeVideoClip, ImageClip

# Инициализируем аудио-микшер Pygame для работы со звуком в реальном времени
pygame.mixer.init()


class PyCutProApp:

    def __init__(self, root):
        self.root = root
        self.root.title("PyCut Pro — Фикс Форматов и Стабильный Экспорт")

        # Ограничения и геометрия окна
        self.root.geometry("1150x850")
        self.root.minsize(1050, 750)
        self.root.configure(bg="#121214")

        # Ядро нелинейного монтажа
        self.video_clip = None
        self.clip_chain = []
        self.modified_clip = None
        self.audio_clip = None
        self.mute_original = False

        # База данных наложений (текст, фото, гифки)
        self.overlay_list = []
        self.temp_files_to_clean = []

        # Путь к временному файлу звука для превью плеера
        self.temp_audio_path = "temp_preview_audio.mp3"

        # Движок плеера
        self.is_playing = False
        self.current_time = 0.0
        self.last_update_time = 0.0
        self.start_playback_time = 0.0

        self.setup_styles()
        self.build_layout()

        self.video_canvas.bind("<Configure>", self.on_canvas_resize)
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

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

        # Добавим Canvas и Scrollbar для левой панели, чтобы всё гарантированно помещалось
        left_canvas = tk.Canvas(self.left_panel, bg="#18181c", highlightthickness=0)
        left_scrollbar = ttk.Scrollbar(self.left_panel, orient="vertical", command=left_canvas.yview)
        scroll_frame = tk.Frame(left_canvas, bg="#18181c", padx=5)

        scroll_frame.bind(
            "<Configure>",
            lambda e: left_canvas.configure(scrollregion=left_canvas.bbox("all"))
        )
        left_canvas.create_window((0, 0), window=scroll_frame, anchor="nw", width=360)
        left_canvas.configure(yscrollcommand=left_scrollbar.set)

        left_canvas.pack(side="left", fill="both", expand=True)
        left_scrollbar.pack(side="right", fill="y")

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

        # 2. Форматы
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

        # 3. Аудиомикшер проекта
        audio_frame = tk.LabelFrame(
            scroll_frame,
            text=" 3. Аудиомикшер проекта ",
            bg="#202024",
            fg="#a0a0a5",
            pady=8,
            padx=8,
        )
        audio_frame.pack(fill="x", pady=6)

        tk.Label(
            audio_frame, text="Громкость микса дорожек:", bg="#202024", fg="white"
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
            text="❌ Удалить мою музыку",
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

        # 5. Новое: Система наложений (Текст / Изображения / GIF)
        overlay_mgmt_frame = tk.LabelFrame(
            scroll_frame,
            text=" 5. Визуальные эффекты и слои ",
            bg="#202024",
            fg="#a0a0a5",
            pady=8,
            padx=8,
        )
        overlay_mgmt_frame.pack(fill="x", pady=6)

        ttk.Button(
            overlay_mgmt_frame,
            text="✨ Открыть окно «Наложение»",
            style="Export.TButton",
            command=self.open_overlay_window,
        ).pack(fill="x", pady=2)

        # 6. Настройка качества сохранения
        export_cfg_frame = tk.LabelFrame(
            scroll_frame,
            text=" 6. Качество сохранения ",
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
        self.lbl_media_info.pack(fill="x", pady=10)

        # ПРАВАЯ ПАНЕЛЬ ПЛЕЕРА
        self.player_panel = tk.Frame(top_paned, bg="#18181c")
        top_paned.add(self.player_panel, width=730)

        preview_container = tk.Frame(self.player_panel, bg="#18181c")
        preview_container.pack(fill="both", expand=True, padx=10, pady=10)

        self.video_canvas = tk.Canvas(
            preview_container, bg="black", highlightthickness=0
        )
        self.video_canvas.pack(side="left", fill="both", expand=True)

        # Вертикальный ползунок громкости превью
        self.preview_volume_slider = tk.Scale(
            preview_container,
            from_=100,
            to=0,
            orient="vertical",
            bg="#18181c",
            fg="#00febe",
            troughcolor="#141416",
            activebackground="#3a3a40",
            highlightthickness=0,
            label="🔊",
            font=("Arial", 9, "bold"),
            command=self.on_preview_volume_changed,
        )
        self.preview_volume_slider.set(70)
        self.preview_volume_slider.pack(side="right", fill="y", padx=(5, 0))

        player_ctrls = tk.Frame(self.player_panel, bg="#18181c")
        player_ctrls.pack(fill="x", pady=5)

        self.btn_play = ttk.Button(
            player_ctrls, text="▶ PLAY", style="CapCut.TButton", width=10, command=self.play_video
        )
        self.btn_play.pack(side="left", padx=10)

        self.btn_pause = ttk.Button(
            player_ctrls, text="⏸ PAUSE", style="CapCut.TButton", width=10, command=self.pause_video
        )
        self.btn_pause.pack(side="left")

        self.btn_stop = ttk.Button(
            player_ctrls, text="⏹ STOP", style="CapCut.TButton", width=10, command=self.stop_video
        )
        self.btn_stop.pack(side="left", padx=5)

        self.btn_cut = ttk.Button(
            player_ctrls, text="✂ РАЗРЕЗАТЬ фрагмент", style="Cut.TButton", command=self.split_active_clip
        )
        self.btn_cut.pack(side="left", padx=20)

        self.lbl_time_digital = tk.Label(
            player_ctrls, text="00:00.00 / 00:00.00", bg="#18181c", fg="white", font=("Consolas", 11)
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
    # ЯДРО ОБРАБОТКИ, КРОПА И СЛОЕВ
    # ==========================================

    def apply_modifications(self):
        """Собирает фрагменты, режет формат и накладывает дополнительные слои (Текст/Фото/GIF)"""
        if not self.clip_chain:
            return

        try:
            if len(self.clip_chain) > 1:
                base_clip = concatenate_videoclips(self.clip_chain, method="compose")
            else:
                base_clip = self.clip_chain[0]

            # Кадрирование соотношения сторон
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
                        new_w = int(curr_h * target_ratio)
                        new_w = new_w - (new_w % 2)
                        x1 = (curr_w - new_w) // 2
                        x2 = x1 + new_w
                        y1 = 0
                        y2 = curr_h
                    else:
                        new_h = int(curr_w / target_ratio)
                        new_h = new_h - (new_h % 2)
                        x1 = 0
                        x2 = curr_w
                        y1 = (curr_h - new_h) // 2
                        y2 = y1 + new_h

                    if hasattr(base_clip, "cropped"):
                        base_clip = base_clip.cropped(x1=x1, y1=y1, x2=x2, y2=y2)
                    else:
                        base_clip = base_clip.crop(x1=x1, y1=y1, x2=x2, y2=y2)

            # Настройка звука видеофрагмента
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

            # НАЛОЖЕНИЕ СЛОЕВ (ТЕКСТ / ФОТО / GIF)
            if self.overlay_list:
                comp_clips = [base_clip]

                for idx, ov in enumerate(self.overlay_list):
                    try:
                        # Фиксация лимитов времени наложения под хронометраж видео
                        start_t = min(ov['start'], base_clip.duration)
                        dur_t = min(ov['duration'], base_clip.duration - start_t)
                        if dur_t <= 0:
                            continue

                        if ov['type'] == 'text':
                            # Безопасный рендеринг текста через PIL без ImageMagick
                            font_size = ov['size']
                            text = ov['text']
                            color = ov['color']
                            font_path = ov['font']

                            try:
                                font = ImageFont.truetype(font_path,
                                                          font_size) if font_path else ImageFont.load_default()
                            except:
                                font = ImageFont.load_default()

                            im_dummy = Image.new("RGBA", (1, 1))
                            draw_dummy = ImageDraw.Draw(im_dummy)
                            bbox = draw_dummy.textbbox((0, 0), text, font=font)
                            tw = (bbox[2] - bbox[0]) + 30
                            th = (bbox[3] - bbox[1]) + 30

                            txt_img = Image.new("RGBA", (tw, th), (0, 0, 0, 0))
                            draw = ImageDraw.Draw(txt_img)
                            draw.text((15, 15), text, fill=color, font=font)

                            t_path = f"temp_layer_{idx}_{uuid.uuid4().hex[:6]}.png"
                            txt_img.save(t_path)
                            self.temp_files_to_clean.append(t_path)

                            layer_clip = ImageClip(t_path)
                            layer_clip = layer_clip.with_start(start_t).with_duration(dur_t)
                            layer_clip = layer_clip.with_position(ov['position'])
                            comp_clips.append(layer_clip)

                        elif ov['type'] == 'media':
                            path = ov['path']
                            if path.lower().endswith('.gif'):
                                layer_clip = VideoFileClip(path, has_mask=True)
                            else:
                                layer_clip = ImageClip(path)

                            layer_clip = layer_clip.with_start(start_t).with_duration(dur_t)
                            layer_clip = layer_clip.with_position(ov['position'])

                            # Умный ресайз: если наложение больше видео, ужимаем его до 35% от ширины экрана
                            if layer_clip.w > base_clip.w or layer_clip.h > base_clip.h:
                                target_w = int(base_clip.w * 0.35)
                                if hasattr(layer_clip, "resized"):
                                    layer_clip = layer_clip.resized(width=target_w)
                                else:
                                    layer_clip = layer_clip.resize(width=target_w)

                            comp_clips.append(layer_clip)

                    except Exception as e_ov:
                        print(f"Ошибка компиляции слоя наложения: {e_ov}")

                base_clip = CompositeVideoClip(comp_clips, size=(base_clip.w, base_clip.h))

            self.modified_clip = base_clip

            self.time_slider.config(from_=0, to=self.modified_clip.duration)
            if self.current_time > self.modified_clip.duration:
                self.current_time = self.modified_clip.duration
                self.time_slider.set(self.current_time)

            self.lbl_media_info.config(
                text=f"Фрагментов в склейке: {len(self.clip_chain)} | Длина: {self.modified_clip.duration:.2f} сек",
                fg="#00febe",
            )

            # Генерация аудиофайла предпросмотра
            try:
                if pygame.mixer.music.get_busy():
                    pygame.mixer.music.stop()
                pygame.mixer.music.unload()
            except:
                pass

            if self.modified_clip.audio is not None:
                try:
                    self.modified_clip.audio.write_audiofile(self.temp_audio_path, logger=None)
                    pygame.mixer.music.load(self.temp_audio_path)
                    self.on_preview_volume_changed(self.preview_volume_slider.get())
                except:
                    pass

        except Exception as e:
            print(f"Ошибка сборки проекта: {e}")

    # ==========================================
    # ИНТЕРФЕЙС ОКНА НАЛОЖЕНИЙ (ДОБАВЛЕНО)
    # ==========================================

    def open_overlay_window(self):
        """Открывает отдельное независимое окно для работы с текстом, фото и GIF библиотеками"""
        if not self.video_clip:
            return messagebox.showerror("Ошибка", "Сначала импортируйте исходное видео!")

        ov_win = tk.Toplevel(self.root)
        ov_win.title("Менеджер наложений — Слои видео")
        ov_win.geometry("800x480")
        ov_win.configure(bg="#18181c")
        ov_win.transient(self.root)
        ov_win.grab_set()

        # Левая часть окна: Список активных слоев
        list_frame = tk.Frame(ov_win, bg="#18181c", width=260)
        list_frame.pack(side="left", fill="both", expand=False, padx=15, pady=15)

        tk.Label(list_frame, text="Текущие слои проекта:", bg="#18181c", fg="white", font=("Arial", 10, "bold")).pack(
            anchor="w")

        lb_layers = tk.Listbox(list_frame, bg="#202024", fg="white", selectbackground="#00febe",
                               selectforeground="black", bd=0, highlightthickness=0, font=("Arial", 9))
        lb_layers.pack(fill="both", expand=True, pady=8)

        def refresh_box():
            lb_layers.delete(0, tk.END)
            for i, item in enumerate(self.overlay_list):
                if item['type'] == 'text':
                    lb_layers.insert(tk.END, f"[{i + 1}] Текст: \"{item['text'][:12]}...\"")
                else:
                    lb_layers.insert(tk.END, f"[{i + 1}] Медиа: {os.path.basename(item['path'])[:15]}")

        def delete_layer():
            sel = lb_layers.curselection()
            if not sel:
                return messagebox.showwarning("Выбор", "Выберите слой из списка для удаления!")
            idx = sel[0]
            self.overlay_list.pop(idx)
            refresh_box()
            self.apply_modifications()
            self.show_frame_at_time(self.current_time)

        ttk.Button(list_frame, text="🗑 Удалить выбранный слой", style="Cut.TButton", command=delete_layer).pack(
            fill="x")

        # Правая часть окна: Панель создания с вкладками
        tabs_frame = tk.Frame(ov_win, bg="#18181c")
        tabs_frame.pack(side="right", fill="both", expand=True, padx=15, pady=15)

        notebook = ttk.Notebook(tabs_frame)
        notebook.pack(fill="both", expand=True)

        # ВКЛАДКА 1: ТЕКСТОВАЯ БИБЛИОТЕКА
        txt_tab = tk.Frame(notebook, bg="#202024", padx=12, pady=12)
        notebook.add(txt_tab, text=" 📝 Добавить Текст ")

        # Мини-библиотека быстрых шаблонов текста
        lib_frame = tk.Frame(txt_tab, bg="#202024")
        lib_frame.pack(fill="x", pady=(0, 10))
        tk.Label(lib_frame, text="Библиотека стилей:", bg="#202024", fg="#a0a0a5").pack(side="left")

        combo_lib = ttk.Combobox(lib_frame,
                                 values=["[Обычный текст]", "🔥 Внимание!", "🎬 Сцена 1", "⭐ WATERMARK", "📱 Подпишись!"],
                                 state="readonly", width=18)
        combo_lib.set("[Обычный текст]")
        combo_lib.pack(side="left", padx=8)

        tk.Label(txt_tab, text="Ваш текст:", bg="#202024", fg="white").pack(anchor="w")
        ent_txt = tk.Entry(txt_tab, bg="#252529", fg="white", insertbackground="white", bd=1, font=("Arial", 10))
        ent_txt.pack(fill="x", pady=4)
        ent_txt.insert(0, "Текст наложения")

        def apply_template(e):
            sel_t = combo_lib.get()
            if sel_t == "🔥 Внимание!":
                ent_txt.delete(0, tk.END);
                ent_txt.insert(0, "ВНИМАНИЕ!")
                color_lbl.config(bg="red");
                color_lbl.color_val = "red"
            elif sel_t == "🎬 Сцена 1":
                ent_txt.delete(0, tk.END);
                ent_txt.insert(0, "СЦЕНА 1 / КАДР 1")
                color_lbl.config(bg="cyan");
                color_lbl.color_val = "cyan"
            elif sel_t == "⭐ WATERMARK":
                ent_txt.delete(0, tk.END);
                ent_txt.insert(0, "@PyCut_Pro_Project")
                color_lbl.config(bg="gray");
                color_lbl.color_val = "gray"
            elif sel_t == "📱 Подпишись!":
                ent_txt.delete(0, tk.END);
                ent_txt.insert(0, "ПОДПИСЫВАЙТЕСЬ!")
                color_lbl.config(bg="yellow");
                color_lbl.color_val = "yellow"

        combo_lib.bind("<<ComboboxSelected>>", apply_template)

        # Кастомный шрифт
        font_frame = tk.Frame(txt_tab, bg="#202024")
        font_frame.pack(fill="x", pady=6)
        tk.Label(font_frame, text="Шрифт (.ttf):", bg="#202024", fg="white").pack(side="left")
        lbl_f_path = tk.Label(font_frame, text="Системный шрифт", bg="#252529", fg="#a0a0a5", anchor="w", padx=5,
                              width=22)
        lbl_f_path.pack(side="left", padx=6, fill="x", expand=True)
        lbl_f_path.font_val = ""

        def load_ttf():
            fp = filedialog.askopenfilename(filetypes=[("TrueType Fonts", "*.ttf *.otf")])
            if fp:
                lbl_f_path.config(text=os.path.basename(fp))
                lbl_f_path.font_val = fp

        ttk.Button(font_frame, text="Обзор", style="CapCut.TButton", command=load_ttf).pack(side="right")

        # Настройки цвета и размера
        settings_frame = tk.Frame(txt_tab, bg="#202024")
        settings_frame.pack(fill="x", pady=6)

        tk.Label(settings_frame, text="Цвет:", bg="#202024", fg="white").grid(row=0, column=0, sticky="w")
        color_lbl = tk.Label(settings_frame, bg="white", width=4, bd=1, relief="solid")
        color_lbl.color_val = "white"
        color_lbl.grid(row=0, column=1, padx=6)

        def pick_color():
            cp = colorchooser.askcolor(color=color_lbl.color_val)
            if cp[1]:
                color_lbl.config(bg=cp[1])
                color_lbl.color_val = cp[1]

        tk.Button(settings_frame, text="Выбрать", bg="#3a3a40", fg="white", font=("Arial", 8), command=pick_color).grid(
            row=0, column=2, padx=2)

        tk.Label(settings_frame, text="Размер:", bg="#202024", fg="white").grid(row=0, column=3, padx=(15, 5))
        sp_size = tk.Spinbox(settings_frame, from_=12, to=250, width=5, bg="#252529", fg="white",
                             buttonbackground="#202024")
        sp_size.delete(0, tk.END);
        sp_size.insert(0, "45")
        sp_size.grid(row=0, column=4)

        # Тайминг и позиция текста
        t_frame = tk.Frame(txt_tab, bg="#202024")
        t_frame.pack(fill="x", pady=8)

        tk.Label(t_frame, text="Старт (сек):", bg="#202024", fg="white").grid(row=0, column=0, sticky="w")
        en_start = tk.Entry(t_frame, bg="#252529", fg="white", width=6)
        en_start.insert(0, "0.0")
        en_start.grid(row=0, column=1, padx=4)

        tk.Label(t_frame, text="Длина (сек):", bg="#202024", fg="white").grid(row=0, column=2, padx=(10, 4))
        en_dur = tk.Entry(t_frame, bg="#252529", fg="white", width=6)
        en_dur.insert(0, f"{self.modified_clip.duration:.1f}")
        en_dur.grid(row=0, column=3)

        tk.Label(t_frame, text="Размещение:", bg="#202024", fg="white").grid(row=1, column=0, pady=10, sticky="w")
        cb_pos = ttk.Combobox(t_frame, values=["center", "top", "bottom", "left", "right"], width=10, state="readonly")
        cb_pos.set("center")
        cb_pos.grid(row=1, column=1, columnspan=2, pady=10, sticky="w")

        def save_txt_layer():
            if not ent_txt.get(): return
            self.overlay_list.append({
                'type': 'text',
                'text': ent_txt.get(),
                'font': lbl_f_path.font_val,
                'color': color_lbl.color_val,
                'size': int(sp_size.get()),
                'start': float(en_start.get() or 0.0),
                'duration': float(en_dur.get() or 5.0),
                'position': cb_pos.get()
            })
            refresh_box()
            self.apply_modifications()
            self.show_frame_at_time(self.current_time)

        ttk.Button(txt_tab, text="➕ Наложить текст на видео", style="Export.TButton", command=save_txt_layer).pack(
            fill="x", side="bottom")

        # ВКЛАДКА 2: ИМПОРТ ФОТО / GIF
        media_tab = tk.Frame(notebook, bg="#202024", padx=12, pady=12)
        notebook.add(media_tab, text=" 🖼 Наложение ФОТО / GIF ")

        media_file_frame = tk.Frame(media_tab, bg="#202024")
        media_file_frame.pack(fill="x", pady=(0, 10))

        tk.Label(media_file_frame, text="Файл наложения (Фотографий/Картинок или анимаций GIF):", bg="#202024",
                 fg="white").pack(anchor="w", pady=2)
        lbl_m_path = tk.Label(media_file_frame, text="Файл не выбран (.png, .jpg, .gif)", bg="#252529", fg="#a0a0a5",
                              anchor="w", padx=6, height=2)
        lbl_m_path.pack(fill="x", side="left", expand=True, pady=4)
        lbl_m_path.file_val = ""

        def load_media():
            mp = filedialog.askopenfilename(filetypes=[("Изображения и GIF", "*.png *.jpg *.jpeg *.gif")])
            if mp:
                lbl_m_path.config(text=os.path.basename(mp), fg="#00febe")
                lbl_m_path.file_val = mp

        ttk.Button(media_file_frame, text="📁 Выбрать файл", style="CapCut.TButton", command=load_media).pack(
            side="right", padx=5)

        # Настройки тайминга и координат для фото/гиф
        m_t_frame = tk.Frame(media_tab, bg="#202024")
        m_t_frame.pack(fill="x", pady=10)

        tk.Label(m_t_frame, text="Старт (сек):", bg="#202024", fg="white").grid(row=0, column=0, sticky="w")
        en_m_start = tk.Entry(m_t_frame, bg="#252529", fg="white", width=6)
        en_m_start.insert(0, "0.0")
        en_m_start.grid(row=0, column=1, padx=4)

        tk.Label(m_t_frame, text="Длина (сек):", bg="#202024", fg="white").grid(row=0, column=2, padx=(10, 4))
        en_m_dur = tk.Entry(m_t_frame, bg="#252529", fg="white", width=6)
        en_m_dur.insert(0, f"{self.modified_clip.duration:.1f}")
        en_m_dur.grid(row=0, column=3)

        tk.Label(m_t_frame, text="Позиция на экране:", bg="#202024", fg="white").grid(row=1, column=0, pady=12,
                                                                                      sticky="w")
        cb_m_pos = ttk.Combobox(m_t_frame, values=["center", "top", "bottom", "left", "right"], width=10,
                                state="readonly")
        cb_m_pos.set("center")
        cb_m_pos.grid(row=1, column=1, columnspan=2, pady=12, sticky="w")

        def save_media_layer():
            if not lbl_m_path.file_val:
                return messagebox.showwarning("Файл", "Сначала выберите файл изображения или GIF!")
            self.overlay_list.append({
                'type': 'media',
                'path': lbl_m_path.file_val,
                'start': float(en_m_start.get() or 0.0),
                'duration': float(en_m_dur.get() or 5.0),
                'position': cb_m_pos.get()
            })
            refresh_box()
            self.apply_modifications()
            self.show_frame_at_time(self.current_time)

        ttk.Button(media_tab, text="➕ Применить фото / GIF слой", style="Export.TButton",
                   command=save_media_layer).pack(fill="x", side="bottom")

        # Стартовая отрисовка активных элементов
        refresh_box()

    # ==========================================
    # НАБОР ФУНКЦИЙ НАВЕРАНИЯ И ПЛЕЕРА
    # ==========================================

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
                    messagebox.showwarning("Нарезка", "Нельзя резать на краях фрагментов!")
                    return

                part_a = clip.subclipped(0, local_t)
                part_b = clip.subclipped(local_t, clip.duration)

                self.clip_chain[idx] = part_a
                self.clip_chain.insert(idx + 1, part_b)

                self.pause_video()
                self.apply_modifications()
                self.show_frame_at_time(self.current_time)
                messagebox.showinfo("Нарезка", f"Разрезано в точке {t:.2f} сек!")
                return
            accumulated_time += clip_duration

    def restore_original_audio(self):
        if not self.video_clip:
            return
        self.audio_clip = None
        self.apply_modifications()
        self.show_frame_at_time(self.current_time)
        messagebox.showinfo("Аудио", "Родной трек восстановлен!")

    def import_video(self):
        file_path = filedialog.askopenfilename(filetypes=[("Video Files", "*.mp4 *.avi *.mov *.mkv")])
        if not file_path:
            return

        self.pause_video()
        self.video_clip = VideoFileClip(file_path)
        self.clip_chain = [self.video_clip]

        self.volume_slider.set(100)
        self.speed_combo.set("1.0")
        self.ratio_combo.set("Original")
        self.mute_original = False
        self.overlay_list.clear()

        self.apply_modifications()
        self.time_slider.set(0)
        self.current_time = 0.0
        self.show_frame_at_time(0)

    def import_audio(self):
        if not self.video_clip:
            return messagebox.showerror("Ошибка", "Сначала импортируйте видео!")
        file_path = filedialog.askopenfilename(filetypes=[("Audio Files", "*.mp3 *.wav")])
        if not file_path:
            return
        try:
            self.audio_clip = AudioFileClip(file_path)
            if self.audio_clip.duration > self.modified_clip.duration:
                self.audio_clip = self.audio_clip.subclipped(0, self.modified_clip.duration)
            self.apply_modifications()
            messagebox.showinfo("Звук", "Музыка добавлена!")
        except Exception as e:
            messagebox.showerror("Ошибка аудио", str(e))

    def toggle_mute(self):
        if not self.video_clip:
            return
        self.mute_original = not self.mute_original
        self.btn_mute.config(text="🔊 Вернуть аудио" if self.mute_original else "🔇 Заглушить всё видео")
        self.apply_modifications()
        self.show_frame_at_time(self.current_time)

    def on_param_changed(self, *args):
        if self.video_clip:
            self.apply_modifications()
            self.show_frame_at_time(self.current_time)

    def on_preview_volume_changed(self, val):
        volume = float(val) / 100.0
        if pygame.mixer.get_init():
            try:
                pygame.mixer.music.set_volume(volume)
            except:
                pass

    def show_frame_at_time(self, t):
        if not self.modified_clip:
            return

        if t < 0: t = 0
        if t > self.modified_clip.duration: t = self.modified_clip.duration

        frame_array = self.modified_clip.get_frame(t)
        img = Image.fromarray(frame_array)

        canvas_width = self.video_canvas.winfo_width()
        canvas_height = self.video_canvas.winfo_height()

        if canvas_width < 100 or canvas_height < 100:
            canvas_width, canvas_height = 730, 410

        img.thumbnail((canvas_width, canvas_height), Image.Resampling.LANCZOS)
        self.tk_image = ImageTk.PhotoImage(img)

        self.video_canvas.delete("all")
        self.video_canvas.create_image(
            canvas_width // 2, canvas_height // 2, anchor="center", image=self.tk_image
        )
        self.lbl_time_digital.config(text=f"{t:.2f}s / {self.modified_clip.duration:.2f}s")

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
            self.start_playback_time = self.current_time

            if self.modified_clip.audio is not None and os.path.exists(self.temp_audio_path):
                try:
                    pygame.mixer.music.play(start=self.current_time)
                except:
                    pass

            self.last_update_time = time.time()
            self.update_player_loop()

    def pause_video(self):
        if self.is_playing:
            self.is_playing = False
            try:
                pygame.mixer.music.stop()
            except:
                pass

    def stop_video(self):
        self.is_playing = False
        try:
            pygame.mixer.music.stop()
        except:
            pass
        self.current_time = 0.0
        self.time_slider.set(0)
        if self.modified_clip:
            self.show_frame_at_time(0)

    def update_player_loop(self):
        if not self.is_playing or not self.modified_clip:
            return

        if self.modified_clip.audio is not None and pygame.mixer.music.get_busy():
            played_time = pygame.mixer.music.get_pos() / 1000.0
            if played_time < 0:
                now = time.time()
                delta = now - self.last_update_time
                self.last_update_time = now
                self.current_time += delta
            else:
                self.current_time = self.start_playback_time + played_time
        else:
            now = time.time()
            delta = now - self.last_update_time
            self.last_update_time = now
            self.current_time += delta

        if self.current_time >= self.modified_clip.duration:
            self.current_time = self.modified_clip.duration
            self.is_playing = False
            try:
                pygame.mixer.music.stop()
            except:
                pass
            self.time_slider.set(self.current_time)
            self.show_frame_at_time(self.current_time)
            return

        self.time_slider.set(self.current_time)
        self.show_frame_at_time(self.current_time)
        self.root.after(10, self.update_player_loop)

    # ==========================================
    # НАДЕЖНЫЙ ЭКСПОРТ
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

        if "1080p" in quality:
            h = 1080
            w = int(export_clip.w * (h / export_clip.h))
            w = w - (w % 2)
            export_clip = export_clip.resized(width=w, height=h) if hasattr(export_clip,
                                                                            "resized") else export_clip.resize(width=w,
                                                                                                               height=h)
        elif "720p" in quality:
            h = 720
            w = int(export_clip.w * (h / export_clip.h))
            w = w - (w % 2)
            export_clip = export_clip.resized(width=w, height=h) if hasattr(export_clip,
                                                                            "resized") else export_clip.resize(width=w,
                                                                                                               height=h)
        elif "480p" in quality:
            h = 480
            w = int(export_clip.w * (h / export_clip.h))
            w = w - (w % 2)
            export_clip = export_clip.resized(width=w, height=h) if hasattr(export_clip,
                                                                            "resized") else export_clip.resize(width=w,
                                                                                                               height=h)
        else:
            if export_clip.w % 2 != 0 or export_clip.h % 2 != 0:
                w = export_clip.w - (export_clip.w % 2)
                h = export_clip.h - (export_clip.h % 2)
                export_clip = export_clip.resized(width=w, height=h) if hasattr(export_clip,
                                                                                "resized") else export_clip.resize(
                    width=w, height=h)

        info_window = tk.Toplevel(self.root)
        info_window.title("Экспорт...")
        info_window.geometry("420x130")
        info_window.configure(bg="#18181c")
        info_window.transient(self.root)
        info_window.grab_set()

        tk.Label(
            info_window,
            text=f"🎬 Идет компиляция фильма...\nПрофиль: {quality}\nПожалуйста, подождите.",
            bg="#18181c", fg="#00febe", font=("Arial", 10, "bold"), pady=25
        ).pack()
        self.root.update()

        try:
            export_clip.write_videofile(
                save_path, codec="libx264", audio_codec="aac", fps=24, threads=4
            )
            info_window.destroy()
            messagebox.showinfo("Готово!", f"Видео успешно сохранено:\n{save_path}")
            self.apply_modifications()
        except Exception as e:
            info_window.destroy()
            messagebox.showerror("Ошибка FFMPEG", f"Ошибка рендеринга: {str(e)}")

    def on_closing(self):
        """Полная деструкция и очистка системы при закрытии"""
        self.is_playing = False
        try:
            pygame.mixer.music.stop()
            pygame.mixer.music.unload()
            pygame.mixer.quit()
        except:
            pass

        # Удаляем временные файлы треков
        if os.path.exists(self.temp_audio_path):
            try:
                os.remove(self.temp_audio_path)
            except:
                pass

        # Удаляем временные маски текста
        for temp_f in self.temp_files_to_clean:
            if os.path.exists(temp_f):
                try:
                    os.remove(temp_f)
                except:
                    pass

        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = PyCutProApp(root)
    root.update()
    root.mainloop()
