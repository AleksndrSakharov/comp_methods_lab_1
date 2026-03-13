import json
import os
import subprocess
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk

plt.rcParams["toolbar"] = "None"
plt.rcParams["font.family"] = "Segoe UI"



class RoundedFrame(tk.Canvas):
    def __init__(self, parent, bg_color="#ffffff", corner_radius=10, padding=10, autoresize=True, **kwargs):
        super().__init__(parent, highlightthickness=0, borderwidth=0, **kwargs)
        self.bg_color = bg_color
        self.corner_radius = corner_radius
        self.padding = padding
        self.autoresize = autoresize
        
        self.rect_id = None
        self.bind("<Configure>", self._on_resize)
        
        # Container for widgets
        self.inner_frame = ttk.Frame(self, style="Card.TFrame")
        self.window_id = self.create_window(0, 0, window=self.inner_frame, anchor="nw")
        
        # Auto-resize canvas to fit inner frame
        self.inner_frame.bind("<Configure>", self._on_inner_configure)

    def _on_inner_configure(self, event):
        if not self.autoresize: return
        
        req_height = event.height + 2 * self.padding
        current_height = self.winfo_height()
        
        if abs(current_height - req_height) > 4:
            self.configure(height=req_height)

    def _on_resize(self, event):
        w, h = event.width, event.height
        self._draw_background(w, h)
        
        iw = w - 2 * self.padding
        ih = h - 2 * self.padding
        
        if iw < 1: iw = 1
        if ih < 1: ih = 1
        
        # Force inner frame to match canvas size
        self.itemconfigure(self.window_id, width=iw, height=ih)
        self.coords(self.window_id, self.padding, self.padding)

    def _draw_background(self, w, h):
        self.delete("bg_rect")
        # Draw rounded rect
        r = self.corner_radius
    
        # 1. Main body rectangles
        self.create_rectangle(r, 0, w-r, h, fill=self.bg_color, outline=self.bg_color, tags="bg_rect")
        self.create_rectangle(0, r, w, h-r, fill=self.bg_color, outline=self.bg_color, tags="bg_rect")
        
        # 2. Corners using oval (circle arcs)
        self.create_oval(0, 0, 2*r, 2*r, fill=self.bg_color, outline=self.bg_color, tags="bg_rect")
        self.create_oval(w-2*r, 0, w, 2*r, fill=self.bg_color, outline=self.bg_color, tags="bg_rect")
        self.create_oval(0, h-2*r, 2*r, h, fill=self.bg_color, outline=self.bg_color, tags="bg_rect")
        self.create_oval(w-2*r, h-2*r, w, h, fill=self.bg_color, outline=self.bg_color, tags="bg_rect")



class RoundedButton(tk.Canvas):
    def __init__(self, parent, text, command=None, width=120, height=36, 
                 bg_color="#3b82f6", fg_color="white", hover_color="#2563eb", corner_radius=18):
        
        # Determine parent background color safely
        try:
            parent_bg = parent["background"]
        except tk.TclError:
            # Fallback for ttk widgets or if unavailable
            try:
                style = ttk.Style()
                parent_bg = style.lookup("TFrame", "background")
            except:
                parent_bg = "#ffffff" # Default fallback
                
        # Fix: ensure parent_bg is valid color string (sometimes lookup returns empty)
        if not parent_bg:
             parent_bg = "#ffffff"

        super().__init__(parent, width=width, height=height, highlightthickness=0, borderwidth=0, bg=parent_bg)
        self.command = command
        self.text = text
        self.bg_color = bg_color
        self.fg_color = fg_color
        self.hover_color = hover_color
        self.corner_radius = corner_radius
        self.initial_width = width # Store ideal width for minimums

        # Draw initial state
        self.rect_id = self._draw_rounded_rect(0, 0, width, height, corner_radius, bg_color)
        self.text_id = self.create_text(width/2, height/2, text=text, fill=fg_color, font=("Segoe UI", 9, "bold"))
        
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<Button-1>", self._on_click)
        self.bind("<Configure>", self._on_resize)
        
    def _on_resize(self, event):
        w, h = event.width, event.height
        self.delete(self.rect_id)
        self.delete(self.text_id)
        
        self.rect_id = self._draw_rounded_rect(0, 0, w, h, self.corner_radius, self.bg_color)
        self.text_id = self.create_text(w/2, h/2, text=self.text, fill=self.fg_color, font=("Segoe UI", 9, "bold"))
        
    def _draw_rounded_rect(self, x, y, w, h, r, color):
        if w < 2*r or h < 2*r:
            r = min(w/2, h/2)  # Clamp radius 
            
        points = [
            x+r, y,
            x+w-r, y,
            x+w, y,
            x+w, y+r,
            x+w, y+h-r,
            x+w, y+h,
            x+w-r, y+h,
            x+r, y+h,
            x, y+h,
             x, y+h-r,
            x, y+r,
            x, y,
        ]
        return self.create_polygon(points, smooth=True, fill=color, outline=color)

    def _on_enter(self, event):
        self.itemconfig(self.rect_id, fill=self.hover_color, outline=self.hover_color)
        self.config(cursor="hand2")

    def _on_leave(self, event):
        self.itemconfig(self.rect_id, fill=self.bg_color, outline=self.bg_color)
        self.config(cursor="")

    def _on_click(self, event):
        if self.command:
            self.command()


class CustomScrollbar(tk.Canvas):
    def __init__(self, parent, width=14, bg_color="#f3f4f6", thumb_color="#d1d5db", thumb_hover_color="#9ca3af", **kwargs):
        super().__init__(parent, width=width, highlightthickness=0, borderwidth=0, bg=bg_color, **kwargs)
        self.command = None
        self.bg_color = bg_color
        self.thumb_color = thumb_color
        self.thumb_hover_color = thumb_hover_color
        
        self.top = 0.0
        self.bottom = 1.0
        
        # State
        self.dragging = False
        self.drag_start_y = 0
        self.drag_start_top = 0
        
        self.thumb_id = self.create_rectangle(0,0,0,0, width=0) # Placeholder
        
        self.bind("<Button-1>", self._on_press)
        self.bind("<B1-Motion>", self._on_drag)
        self.bind("<ButtonRelease-1>", self._on_release)
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<Configure>", self._on_resize)

    def set(self, lo, hi):
        self.top = float(lo)
        self.bottom = float(hi)
        self._redraw()

    def _redraw(self):
        h = self.winfo_height()
        w = self.winfo_width()
        if h <= 0 or w <= 0: return
        
        y1 = h * self.top
        y2 = h * self.bottom
        
        if y2 - y1 < 10: # Min thumb size
            # If thumb is too small, we center it around the midpoint if possible or just clamp
            mid = (y1 + y2) / 2
            y1 = mid - 5
            y2 = mid + 5
            
        pad = 4
        thumb_w = w - 2*pad
        thumb_h = y2 - y1
        thumb_x = pad
        thumb_y = y1
        
        self.delete("all")
        # Track (optional, transparent bg is fine)
        self.create_rectangle(0, 0, w, h, fill=self.bg_color, outline="", width=0)
        
        if thumb_w > 0 and thumb_h > 0:
            self.thumb_id = self._draw_rounded_rect(thumb_x, thumb_y, thumb_w, thumb_h, 4, self.thumb_color)

    def _draw_rounded_rect(self, x, y, w, h, r, color):
        r = min(r, w/2, h/2)
        points = [
            x+r, y, x+w-r, y, x+w, y, x+w, y+r,
            x+w, y+h-r, x+w, y+h, x+w-r, y+h, x+r, y+h,
            x, y+h, x, y+h-r, x, y+r, x, y
        ]
        return self.create_polygon(points, smooth=True, fill=color, outline="", tags="thumb")

    def _on_resize(self, event):
        self._redraw()

    def _on_press(self, event):
        y = event.y
        h = self.winfo_height()
        if h == 0: return 
        
        y1 = h * self.top
        y2 = h * self.bottom
        
        if y1 <= y <= y2:
            self.dragging = True
            self.drag_start_y = y
            # We want to track delta relative to current scroll position
            # Store the current 'top' fraction
            self.drag_start_top = self.top
            self.itemconfig("thumb", fill=self.thumb_hover_color)
        else:
            # Jump scroll
            pos = y / h
            if self.command:
                self.command("moveto", pos - (self.bottom - self.top)/2)

    def _on_drag(self, event):
        if not self.dragging: return
        
        h = self.winfo_height()
        current_y = event.y
        dy = current_y - self.drag_start_y
        
        dy_frac = dy / h
        new_top = self.drag_start_top + dy_frac
        
        if self.command:
             self.command("moveto", new_top)

    def _on_release(self, event):
        self.dragging = False
        hover = self._is_hovering(event)
        self.itemconfig(self.thumb_id, fill=self.thumb_hover_color if hover else self.thumb_color)

    def _on_enter(self, event):
        self.itemconfig(self.thumb_id, fill=self.thumb_hover_color)

    def _on_leave(self, event):
        if not self.dragging:
             self.itemconfig(self.thumb_id, fill=self.thumb_color)

    def _is_hovering(self, event):
        return 0 <= event.x <= self.winfo_width() and 0 <= event.y <= self.winfo_height()


class LabUI(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Лабораторная 1 · Численные методы")
        self.geometry("1180x800")
        self.minsize(1040, 700)

        self.project_root = Path(__file__).resolve().parent.parent
        self.default_input = self.project_root / "input_examples" / "default_input.json"
        
        # Ensure default Output exists
        self.default_output = self.project_root / "output"
        self.default_output.mkdir(exist_ok=True)

        self.input_path_var = tk.StringVar(value=str(self.default_input))
        self.output_dir_var = tk.StringVar(value=str(self.default_output))
        self.solver_path_var = tk.StringVar(value=str(self._default_solver_path()))
        self._init_parameter_vars()
        self._load_input_file(self.default_input, show_message=False)

        # State for table toggle
        self.current_table_mode = "test"  # 'test' or 'main'

        self._configure_style()
        self._build_ui()

    def _configure_style(self) -> None:
        self.configure(bg="#f3f4f6")
        
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except:
            pass
        
        # Colors
        bg_main = "#f3f4f6"
        bg_card = "#ffffff"
        text_primary = "#1f2937"
        text_secondary = "#6b7280"
        
        style.configure("TFrame", background=bg_main)
        style.configure("Card.TFrame", background=bg_card)
        style.configure("Header.TLabel", font=("Segoe UI", 20, "bold"), background=bg_main, foreground="#111827")
        style.configure("Subheader.TLabel", font=("Segoe UI", 10), background=bg_main, foreground=text_secondary)
        
        # Labels inside cards
        style.configure("Field.TLabel", font=("Segoe UI", 9, "bold"), background=bg_card, foreground="#374151")
        style.configure("Card.TCheckbutton", background=bg_card, foreground=text_primary)
        
        # Entries
        style.configure(
            "TEntry",
            fieldbackground="#f9fafb",
            foreground=text_primary,
            borderwidth=0,
            relief="flat",
            padding=(10, 8),
        )
        
        # Treeview
        style.configure("Treeview", 
            font=("Consolas", 9), 
            rowheight=28, 
            background="#ffffff", 
            fieldbackground="#ffffff",
            foreground=text_primary,
            borderwidth=0
        )
        style.configure("Treeview.Heading", 
            font=("Segoe UI", 9, "bold"), 
            background="#f3f4f6", 
            foreground=text_secondary,
            relief="flat",
            padding=(8, 8)
        )
        style.map("Treeview.Heading", background=[("active", "#e5e7eb")])

    def _solver_candidates(self) -> list[Path]:
        return [
            self.project_root / "build" / "Release" / "lab1_solver.exe",
            self.project_root / "build" / "Debug" / "lab1_solver.exe",
            self.project_root / "build" / "lab1_solver.exe",
        ]

    def _default_solver_path(self) -> Path:
        for candidate in self._solver_candidates():
            if candidate.exists():
                return candidate
        return self._solver_candidates()[0]

    def _try_resolve_solver(self) -> Path | None:
        current = Path(self.solver_path_var.get())
        if current.exists():
            return current

        for candidate in self._solver_candidates():
            if candidate.exists():
                self.solver_path_var.set(str(candidate))
                return candidate
        return None

    def _default_input_payload(self) -> dict:
        return {
            "x0": 0.0,
            "b": 5.0,
            "h0": 0.01,
            "eps": 1e-5,
            "nmax": 100000,
            "adaptive": True,
            "variant": 25,
            "test_u0": 1.0,
            "m": 0.01,
            "c": 0.15,
            "k": 2.0,
            "kStar": 2.0,
            "u0": 10.0,
            "du0": 0.0,
            "kStarValues": [0.0, 1.0, 2.0, 3.0],
            "cValues": [0.0, 0.05, 0.15, 0.3],
        }

    def _init_parameter_vars(self) -> None:
        self.x0_var = tk.StringVar()
        self.b_var = tk.StringVar()
        self.h0_var = tk.StringVar()
        self.eps_var = tk.StringVar()
        self.nmax_var = tk.StringVar()
        self.adaptive_var = tk.BooleanVar(value=True)

        self.variant_var = tk.StringVar()
        self.test_u0_var = tk.StringVar()

        self.mass_var = tk.StringVar()
        self.c_var = tk.StringVar()
        self.k_var = tk.StringVar()
        self.k_star_var = tk.StringVar()
        self.main_u0_var = tk.StringVar()
        self.du0_var = tk.StringVar()

        self.k_star_values_var = tk.StringVar()
        self.c_values_var = tk.StringVar()

    def _set_form_values(self, data: dict) -> None:
        payload = self._default_input_payload()
        payload.update(data)

        self.x0_var.set(str(payload["x0"]))
        self.b_var.set(str(payload["b"]))
        self.h0_var.set(str(payload["h0"]))
        self.eps_var.set(str(payload["eps"]))
        self.nmax_var.set(str(payload["nmax"]))
        self.adaptive_var.set(bool(payload["adaptive"]))

        self.variant_var.set(str(payload["variant"]))
        self.test_u0_var.set(str(payload["test_u0"]))

        self.mass_var.set(str(payload["m"]))
        self.c_var.set(str(payload["c"]))
        self.k_var.set(str(payload["k"]))
        self.k_star_var.set(str(payload["kStar"]))
        self.main_u0_var.set(str(payload["u0"]))
        self.du0_var.set(str(payload["du0"]))

        self.k_star_values_var.set(", ".join(str(value) for value in payload["kStarValues"]))
        self.c_values_var.set(", ".join(str(value) for value in payload["cValues"]))

    def _load_input_file(self, path: Path, show_message: bool = True) -> None:
        if not path.exists():
            if show_message:
                messagebox.showerror("Ошибка", f"Не найден JSON: {path}")
            return

        try:
            with path.open("r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as ex:
            if show_message:
                messagebox.showerror("Ошибка чтения", f"Не удалось загрузить JSON:\n{ex}")
            return

        self.input_path_var.set(str(path))
        self._set_form_values(data)

        if show_message:
            messagebox.showinfo("Загружено", f"Параметры загружены из:\n{path}")

    @staticmethod
    def _parse_float(value: str, field_name: str) -> float:
        text = value.strip().replace(",", ".")
        if not text:
            raise ValueError(f"Поле '{field_name}' должно быть заполнено.")
        try:
            return float(text)
        except ValueError as ex:
            raise ValueError(f"Поле '{field_name}' должно быть числом.") from ex

    @staticmethod
    def _parse_int(value: str, field_name: str) -> int:
        text = value.strip()
        if not text:
            raise ValueError(f"Поле '{field_name}' должно быть заполнено.")
        try:
            return int(text)
        except ValueError as ex:
            raise ValueError(f"Поле '{field_name}' должно быть целым числом.") from ex

    def _parse_series(self, value: str, field_name: str, fallback: list[float]) -> list[float]:
        normalized = value.replace(";", ",")
        parts = [part.strip() for part in normalized.split(",") if part.strip()]
        if not parts:
            return fallback

        result = []
        for part in parts:
            result.append(self._parse_float(part, field_name))
        return result

    def _build_input_payload(self) -> dict:
        x0 = self._parse_float(self.x0_var.get(), "x0")
        b = self._parse_float(self.b_var.get(), "b")
        h0 = self._parse_float(self.h0_var.get(), "h0")
        eps = self._parse_float(self.eps_var.get(), "eps")
        nmax = self._parse_int(self.nmax_var.get(), "nmax")

        variant = self._parse_int(self.variant_var.get(), "variant")
        test_u0 = self._parse_float(self.test_u0_var.get(), "u0 тестовой задачи")

        mass = self._parse_float(self.mass_var.get(), "m")
        damping = self._parse_float(self.c_var.get(), "c")
        stiffness = self._parse_float(self.k_var.get(), "k")
        stiffness_star = self._parse_float(self.k_star_var.get(), "k*")
        main_u0 = self._parse_float(self.main_u0_var.get(), "u0 основной задачи")
        du0 = self._parse_float(self.du0_var.get(), "u'0")

        if b <= x0:
            raise ValueError("Правая граница b должна быть больше x0.")
        if h0 <= 0.0:
            raise ValueError("Начальный шаг h0 должен быть положительным.")
        if eps <= 0.0:
            raise ValueError("Параметр eps должен быть положительным.")
        if nmax <= 0:
            raise ValueError("Максимальное число шагов nmax должно быть положительным.")
        if mass <= 0.0:
            raise ValueError("Параметр m должен быть положительным.")

        return {
            "x0": x0,
            "b": b,
            "h0": h0,
            "eps": eps,
            "nmax": nmax,
            "adaptive": self.adaptive_var.get(),
            "variant": variant,
            "test_u0": test_u0,
            "m": mass,
            "c": damping,
            "k": stiffness,
            "kStar": stiffness_star,
            "u0": main_u0,
            "du0": du0,
            "kStarValues": self._parse_series(self.k_star_values_var.get(), "Серия k*", [stiffness_star]),
            "cValues": self._parse_series(self.c_values_var.get(), "Серия c", [damping]),
        }

    def _create_parameter_field(self, parent, label: str, variable: tk.Variable) -> ttk.Frame:
        frame = ttk.Frame(parent, style="Card.TFrame")
        ttk.Label(frame, text=label, style="Field.TLabel").pack(anchor="w", pady=(0, 4))
        ttk.Entry(frame, textvariable=variable, font=("Segoe UI", 9)).pack(fill=tk.X)
        return frame

    def _create_parameter_row(self, parent, left_label: str, left_var: tk.Variable, right_label: str | None = None, right_var: tk.Variable | None = None) -> None:
        row = ttk.Frame(parent, style="Card.TFrame")
        row.pack(fill=tk.X, pady=(0, 8))

        left = self._create_parameter_field(row, left_label, left_var)
        left.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6))

        if right_label is not None and right_var is not None:
            right = self._create_parameter_field(row, right_label, right_var)
            right.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(6, 0))

    def _create_section_title(self, parent, text: str, top_pad: int = 12) -> None:
        ttk.Label(parent, text=text, style="Field.TLabel", font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(top_pad, 8))

    def _bind_mousewheel_scroll(self, widget: tk.Widget, canvas: tk.Canvas) -> None:
        def on_mousewheel(event) -> None:
            canvas.yview_scroll(int(-event.delta / 120), "units")

        def bind_scroll(_event) -> None:
            canvas.bind_all("<MouseWheel>", on_mousewheel)

        def unbind_scroll(_event) -> None:
            canvas.unbind_all("<MouseWheel>")

        widget.bind("<Enter>", bind_scroll)
        widget.bind("<Leave>", unbind_scroll)

    def _build_parameter_form(self, parent) -> None:
        self._create_section_title(parent, "Параметры интегрирования", top_pad=4)
        self._create_parameter_row(parent, "x0", self.x0_var, "b", self.b_var)
        self._create_parameter_row(parent, "h0", self.h0_var, "eps", self.eps_var)

        self._create_parameter_row(parent, "nmax", self.nmax_var)

        adaptive_frame = ttk.Frame(parent, style="Card.TFrame")
        adaptive_frame.pack(fill=tk.X, pady=(0, 8))
        ttk.Label(adaptive_frame, text="Адаптивный шаг", style="Field.TLabel").pack(anchor="w", pady=(0, 4))
        ttk.Checkbutton(adaptive_frame, text="Использовать контроль локальной погрешности", variable=self.adaptive_var, style="Card.TCheckbutton").pack(anchor="w")

        self._create_section_title(parent, "Тестовая задача")
        self._create_parameter_row(parent, "Вариант", self.variant_var, "u0", self.test_u0_var)

        self._create_section_title(parent, "Основная задача")
        self._create_parameter_row(parent, "m", self.mass_var, "c", self.c_var)
        self._create_parameter_row(parent, "k", self.k_var, "k*", self.k_star_var)
        self._create_parameter_row(parent, "u0", self.main_u0_var, "u'0", self.du0_var)

    def _build_ui(self) -> None:
        # Main shell with padding
        shell = ttk.Frame(self)
        shell.pack(fill=tk.BOTH, expand=True, padx=30, pady=30)

        # Header
        header = ttk.Frame(shell)
        header.pack(fill=tk.X, anchor="nw", pady=(0, 20))
        
        ttk.Label(header, text="Численные методы", style="Subheader.TLabel").pack(anchor="w")
        ttk.Label(header, text="Лабораторная работа №1", style="Header.TLabel").pack(anchor="w")
        ttk.Label(header, text="Рунге-Кутта 4-го порядка · Адаптивный шаг", style="Subheader.TLabel").pack(anchor="w", pady=(4, 0))

        # Grid Layout
        grid_frame = ttk.Frame(shell)
        grid_frame.pack(fill=tk.BOTH, expand=True, pady=(20, 0))
        grid_frame.columnconfigure(0, weight=1, minsize=320)  
        grid_frame.columnconfigure(1, weight=3)
        grid_frame.rowconfigure(0, weight=1)

        # Left Column (Config + Actions)
        left_col = ttk.Frame(grid_frame)
        left_col.grid(row=0, column=0, sticky="nsew", padx=(0, 24))

        # Config Card
        self._build_config_card(left_col)
        
        # Spacer
        ttk.Frame(left_col, height=20).pack(fill=tk.X)

        # Actions Card
        self._build_actions_card(left_col)

        # Right Column (Results)
        right_col = ttk.Frame(grid_frame)
        right_col.grid(row=0, column=1, sticky="nsew")
        # Ensure right_col expands
        
        # Summary Card
        self._build_summary_card(right_col)
        
        # Spacer
        ttk.Frame(right_col, height=20).pack()
        
        # Table Card
        self._build_table_card(right_col)

    def _build_config_card(self, parent):
        card = RoundedFrame(parent, bg_color="#ffffff", corner_radius=16, padding=20, autoresize=False, height=600)
        card.pack(fill=tk.X)
        
        inner = card.inner_frame
        
        ttk.Label(inner, text="Конфигурация и ввод", style="Field.TLabel", font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=(0, 16))

        scroll_outer = ttk.Frame(inner, style="Card.TFrame")
        scroll_outer.pack(fill=tk.BOTH, expand=True)

        scroll_canvas = tk.Canvas(scroll_outer, highlightthickness=0, borderwidth=0, background="#ffffff")
        scroll_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scroll_bar = CustomScrollbar(scroll_outer, width=12, bg_color="#ffffff", thumb_color="#d1d5db", thumb_hover_color="#9ca3af")
        scroll_bar.pack(side=tk.RIGHT, fill=tk.Y, pady=2)
        scroll_bar.command = scroll_canvas.yview
        scroll_canvas.configure(yscrollcommand=scroll_bar.set)

        form_inner = ttk.Frame(scroll_canvas, style="Card.TFrame")
        form_window = scroll_canvas.create_window(0, 0, window=form_inner, anchor="nw")

        def update_scroll_region(_event) -> None:
            scroll_canvas.configure(scrollregion=scroll_canvas.bbox("all"))

        def update_inner_width(event) -> None:
            scroll_canvas.itemconfigure(form_window, width=event.width)

        form_inner.bind("<Configure>", update_scroll_region)
        scroll_canvas.bind("<Configure>", update_inner_width)
        self._bind_mousewheel_scroll(scroll_canvas, scroll_canvas)
        self._bind_mousewheel_scroll(form_inner, scroll_canvas)

        self._create_input_field(form_inner, "Solver Executable", self.solver_path_var, self.pick_solver)
        self._create_input_field(form_inner, "JSON шаблон", self.input_path_var, self.pick_input)
        self._create_input_field(form_inner, "Output Directory", self.output_dir_var, self.pick_output)
        self._build_parameter_form(form_inner)
        
        # Run Button
        btn_frame = ttk.Frame(inner, style="Card.TFrame")
        btn_frame.pack(fill=tk.X, pady=(16, 0))
        RoundedButton(btn_frame, text="Запустить расчёт", command=self.run_solver, width=280, bg_color="#3b82f6", hover_color="#2563eb").pack(fill=tk.X)

    def _create_input_field(self, parent, label, var, cmd):
        ttk.Label(parent, text=label, style="Field.TLabel").pack(anchor="w", pady=(0, 4))
        
        cnt = ttk.Frame(parent, style="Card.TFrame")
        cnt.pack(fill=tk.X, pady=(0, 12))
        
        entry = ttk.Entry(cnt, textvariable=var, font=("Segoe UI", 9))
        entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8))
        
        # Small icon button for browse (using a simple button for now, styled simply)
        ttk.Button(cnt, text="...", width=3, command=cmd).pack(side=tk.RIGHT)

    def _build_actions_card(self, parent):
        # Allow vertical expansion
        card = RoundedFrame(parent, bg_color="#ffffff", corner_radius=16, padding=20, autoresize=False)
        card.pack(fill=tk.BOTH, expand=True)
        
        inner = card.inner_frame
        ttk.Label(inner, text="Визуализация", style="Field.TLabel", font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=(0, 16))

        # Grid of buttons
        btn_grid = ttk.Frame(inner, style="Card.TFrame")
        btn_grid.pack(fill=tk.X)
        
        RoundedButton(btn_grid, text="Тестовая задача", command=self.plot_test, 
                      bg_color="#e5e7eb", fg_color="#1f2937", hover_color="#d1d5db", width=280).pack(fill=tk.X, pady=(0, 10))
                      
        RoundedButton(btn_grid, text="Основная (Координаты)", command=self.plot_main, 
                      bg_color="#e5e7eb", fg_color="#1f2937", hover_color="#d1d5db", width=280).pack(fill=tk.X, pady=(0, 10))

        RoundedButton(btn_grid, text="Фазовый портрет", command=self.plot_phase, 
                      bg_color="#e5e7eb", fg_color="#1f2937", hover_color="#d1d5db", width=280).pack(fill=tk.X, pady=(0, 10))

    def _build_summary_card(self, parent):
        card = RoundedFrame(parent, bg_color="#ffffff", corner_radius=16, padding=20, height=260)
        card.pack(fill=tk.X)
        
        inner = card.inner_frame
        ttk.Label(inner, text="Сводка результатов", style="Field.TLabel", font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=(0, 8))

        container = ttk.Frame(inner, style="Card.TFrame")
        container.pack(fill=tk.BOTH, expand=True)

        summary_scrollbar = CustomScrollbar(container, width=12, bg_color="#ffffff", thumb_color="#d1d5db", thumb_hover_color="#9ca3af")
        summary_scrollbar.pack(side=tk.RIGHT, fill=tk.Y, pady=2)

        self.summary_box = tk.Text(
            container,
            height=10,
            wrap=tk.WORD,
            bd=0,
            padx=0,
            pady=0,
            font=("Consolas", 9),
            background="#ffffff",
            foreground="#374151",
            yscrollcommand=summary_scrollbar.set
        )
        self.summary_box.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        summary_scrollbar.command = self.summary_box.yview

    def _build_table_card(self, parent):
        card = RoundedFrame(parent, bg_color="#ffffff", corner_radius=16, padding=20, autoresize=False)
        card.pack(fill=tk.BOTH, expand=True)
        
        inner = card.inner_frame
        
        # Header with toggle buttons
        header_frame = ttk.Frame(inner, style="Card.TFrame")
        header_frame.pack(fill=tk.X, pady=(0, 12))
        
        self.table_title = ttk.Label(header_frame, text="Таблица значений (Тестовая)", style="Field.TLabel", font=("Segoe UI", 12, "bold"))
        self.table_title.pack(side=tk.LEFT)
        
        # Toggle buttons
        toggle_frame = ttk.Frame(header_frame, style="Card.TFrame")
        toggle_frame.pack(side=tk.RIGHT)
        
        RoundedButton(toggle_frame, text="Тестовая", width=80, height=28, 
                      command=lambda: self._switch_table("test"), 
                      bg_color="#e5e7eb", fg_color="#374151", hover_color="#d1d5db", corner_radius=14).pack(side=tk.LEFT, padx=(0, 8))
                      
        RoundedButton(toggle_frame, text="Основная", width=80, height=28, 
                      command=lambda: self._switch_table("main"), 
                      bg_color="#e5e7eb", fg_color="#374151", hover_color="#d1d5db", corner_radius=14).pack(side=tk.LEFT)
        
        container = ttk.Frame(inner, style="Card.TFrame")
        container.pack(fill=tk.BOTH, expand=True)
        
        # Custom scrollbar container
        # Treeview needs to communicate with custom scrollbar
        
        self.scrollbar = CustomScrollbar(container, width=12, bg_color="#ffffff", thumb_color="#d1d5db", thumb_hover_color="#9ca3af")
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y, pady=2)
        
        self.table = ttk.Treeview(container, show="headings", yscrollcommand=self.scrollbar.set)
        
        # Link scrollbar back to table
        self.scrollbar.command = self.table.yview
        
        self.table.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Initial columns
        self._setup_test_columns()

    def _switch_table(self, mode: str):
        if self.current_table_mode == mode: return
        self.current_table_mode = mode
        
        if mode == "test":
            self.table_title.configure(text="Таблица значений (Тестовая)")
            self._setup_test_columns()
        else:
            self.table_title.configure(text="Таблица значений (Основная)")
            self._setup_main_columns()
            
        self._fill_current_table()

    def _setup_test_columns(self):
        # Clear existing
        self.table.delete(*self.table.get_children())
        
        cols = [
            ("i", "i", 40), ("x", "xi", 70), ("vi", "vi", 80), ("v2i", "v2i", 80), ("delta", "vi-v2i", 80),
            ("olp", "ОЛП", 80), ("h", "hi", 70), ("c1", "C1", 40), ("c2", "C2", 40), ("ue", "ui", 80), ("err", "|ui-vi|", 80)
        ]
        self.table["columns"] = [c[0] for c in cols]
        for name, text, w in cols:
            self.table.heading(name, text=text)
            self.table.column(name, width=w, stretch=True)

    def _setup_main_columns(self):
        # Clear existing
        self.table.delete(*self.table.get_children())
        
        cols = [
            ("i", "i", 40), ("x", "xi", 70), ("v1", "u(xi)", 80), ("v2", "u'(xi)", 80), 
            ("v2i_1", "v2_u", 80), ("v2i_2", "v2_u'", 80),
            ("delta1", "du", 80), ("delta2", "du'", 80),
            ("olp", "ОЛП", 80), ("h", "hi", 70), ("c1", "C1", 40), ("c2", "C2", 40)
        ]
        self.table["columns"] = [c[0] for c in cols]
        for name, text, w in cols:
            self.table.heading(name, text=text)
            self.table.column(name, width=w, stretch=True)
            
    def _fill_current_table(self):
        try:
            data = self._read_result()
        except:
             return # No data yet
             
        for item in self.table.get_children():
            self.table.delete(item)
            
        if self.current_table_mode == "test":
            rows = data["test"]["rows"]
            for row in rows:
                v = row["v"][0] if row["v"] else 0.0
                v2 = row["v2"][0] if row["v2"] else 0.0
                d = row["delta"][0] if row["delta"] else 0.0
                self.table.insert("", tk.END, values=(
                    row["i"], f"{row['x']:.6f}", f"{v:.6f}", f"{v2:.6f}", f"{d:.3e}",
                    f"{row['olp']:.3e}", f"{row['h']:.3e}", row["c1"], row["c2"],
                    f"{row.get('uExact', 0.0):.6f}", f"{row.get('absExactError', 0.0):.3e}"
                ))
        else:
            rows = data["main"]["rows"]
            for row in rows:
                u = row["v"][0] if len(row["v"])>0 else 0.0
                du = row["v"][1] if len(row["v"])>1 else 0.0
                
                u2 = row["v2"][0] if len(row["v2"])>0 else 0.0
                du2 = row["v2"][1] if len(row["v2"])>1 else 0.0
                
                del1 = row["delta"][0] if len(row["delta"])>0 else 0.0
                del2 = row["delta"][1] if len(row["delta"])>1 else 0.0
                
                self.table.insert("", tk.END, values=(
                    row["i"], f"{row['x']:.6f}", f"{u:.6f}", f"{du:.6f}",
                    f"{u2:.6f}", f"{du2:.6f}", f"{del1:.3e}", f"{del2:.3e}",
                    f"{row['olp']:.3e}", f"{row['h']:.3e}", row["c1"], row["c2"]
                ))

    def pick_solver(self) -> None:
        path = filedialog.askopenfilename(filetypes=[("Executable", "*.exe"), ("All files", "*.*")])
        if path:
            self.solver_path_var.set(path)

    def pick_input(self) -> None:
        path = filedialog.askopenfilename(filetypes=[("JSON", "*.json")])
        if path:
            self._load_input_file(Path(path))

    def pick_output(self) -> None:
        path = filedialog.askdirectory()
        if path:
            self.output_dir_var.set(path)

    def _result_path(self) -> Path:
        return Path(self.output_dir_var.get()) / "result.json"

    def _read_result(self) -> dict:
        path = self._result_path()
        if not path.exists():
            raise FileNotFoundError(f"Не найден {path}. Сначала запустите расчёт.")
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)

    def run_solver(self) -> None:
        solver = self._try_resolve_solver()
        output_dir = Path(self.output_dir_var.get())

        if solver is None or not solver.exists():
            tried = "\n".join(str(c) for c in self._solver_candidates())
            messagebox.showerror(
                "Ошибка",
                "Не найден solver.\n"
                "Соберите проект командой .\\run.ps1 -Mode build\n\n"
                f"Проверены пути:\n{tried}",
            )
            return
        try:
            payload = self._build_input_payload()
        except ValueError as ex:
            messagebox.showerror("Ошибка ввода", str(ex))
            return

        output_dir.mkdir(parents=True, exist_ok=True)
        input_json = output_dir / "_ui_runtime_input.json"

        try:
            with input_json.open("w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
        except Exception as ex:
            messagebox.showerror("Ошибка", f"Не удалось создать входной JSON:\n{ex}")
            return

        cmd = [str(solver), str(input_json), str(output_dir)]
        try:
            # Use specific encoding for Windows console if possible, but utf-8 is generally safer for JSON
            # However, subprocess text=True uses locale encoding by default?
            completed = subprocess.run(cmd, check=True, capture_output=True, text=True, encoding='utf-8', errors='replace')
        except subprocess.CalledProcessError as ex:
            err_msg = ex.stderr if ex.stderr else (ex.stdout if ex.stdout else str(ex))
            messagebox.showerror("Ошибка запуска", f"Solver failed with code {ex.returncode}:\n{err_msg}")
            return
        except Exception as ex:
            messagebox.showerror("Ошибка", f"Не удалось запустить solver:\n{str(ex)}")
            return
        
        # After successful run, refresh data
        try:
            self.show_summary(completed.stdout)
            self._fill_current_table()
            messagebox.showinfo("Готово", f"Расчёт выполнен. Результаты: {output_dir}")
        except Exception as ex:
             messagebox.showerror("Ошибка отображения", f"Не удалось отобразить результаты:\n{str(ex)}")

    @staticmethod
    def _attach_mouse_navigation(fig: Figure, axes: list) -> None:
        # Use pixel-based dragging to avoid jitter
        state: dict[str, object] = {
            "pressed": False,
            "ax": None,
            "x_start_pix": 0,
            "y_start_pix": 0,
            "xlim_start": (0.0, 0.0),
            "ylim_start": (0.0, 0.0),
        }

        for ax in axes:
            ax.set_navigate(False)

        def on_scroll(event) -> None:
            ax = event.inaxes
            if ax is None: return

            base_scale = 1.2
            if event.button == "up":
                scale_factor = 1.0 / base_scale
            elif event.button == "down":
                scale_factor = base_scale
            else:
                return

            x_left, x_right = ax.get_xlim()
            y_bottom, y_top = ax.get_ylim()

            # Center zoom around mouse cursor
            if event.xdata is not None and event.ydata is not None:
                center_x = event.xdata
                center_y = event.ydata
            else:
                center_x = (x_left + x_right) / 2
                center_y = (y_bottom + y_top) / 2

            new_width = (x_right - x_left) * scale_factor
            new_height = (y_top - y_bottom) * scale_factor

            relx = (center_x - x_left) / (x_right - x_left)
            rely = (center_y - y_bottom) / (y_top - y_bottom)

            ax.set_xlim([center_x - new_width * relx, center_x + new_width * (1 - relx)])
            ax.set_ylim([center_y - new_height * rely, center_y + new_height * (1 - rely)])
            fig.canvas.draw_idle()

        def on_press(event) -> None:
            if event.button != 1 or event.inaxes is None: return
            state["pressed"] = True
            state["ax"] = event.inaxes
            state["x_start_pix"] = event.x
            state["y_start_pix"] = event.y
            state["xlim_start"] = event.inaxes.get_xlim()
            state["ylim_start"] = event.inaxes.get_ylim()

        def on_release(_event) -> None:
            state["pressed"] = False
            state["ax"] = None

        def on_motion(event) -> None:
            if not state["pressed"] or state["ax"] is None: return
            if event.inaxes != state["ax"]: return

            ax = state["ax"]
            # Pixel delta
            dx_pix = event.x - state["x_start_pix"]
            dy_pix = event.y - state["y_start_pix"]

            xlim = state["xlim_start"]
            ylim = state["ylim_start"]
            
            # Convert pixel delta to data delta using scale from START of drag
            # We want to move the view, so opposite direction
            
            bbox = ax.bbox
            width_pix = bbox.width
            height_pix = bbox.height
            
            width_data = xlim[1] - xlim[0]
            height_data = ylim[1] - ylim[0]
            
            dx_data = (dx_pix / width_pix) * width_data
            dy_data = (dy_pix / height_pix) * height_data
            
            ax.set_xlim(xlim[0] - dx_data, xlim[1] - dx_data)
            ax.set_ylim(ylim[0] - dy_data, ylim[1] - dy_data)
            
            fig.canvas.draw_idle()

        fig.canvas.mpl_connect("scroll_event", on_scroll)
        fig.canvas.mpl_connect("button_press_event", on_press)
        fig.canvas.mpl_connect("button_release_event", on_release)
        fig.canvas.mpl_connect("motion_notify_event", on_motion)

    def show_summary(self, header: str = "") -> None:
        try:
            data = self._read_result()
        except Exception as ex:
            messagebox.showerror("Ошибка чтения", str(ex))
            return

        test_s = data["test"]["summary"]
        main_s = data["main"]["summary"]
        lines = []
        if header:
            lines.append(header.strip())
            lines.append("")

        lines.append("Тестовая задача:")
        lines.append(f"n = {test_s['n']}, b - xn = {test_s['bMinusXn']:.6e}")
        lines.append(f"max |ОЛП| = {test_s['maxAbsOLP']:.6e}")
        lines.append(f"Общее число делений h = {test_s['totalDivisions']}")
        lines.append(f"Общее число удвоений h = {test_s['totalDoublings']}")
        lines.append(f"max h = {test_s['maxH']:.6e} при x = {test_s['xAtMaxH']:.6f}")
        lines.append(f"min h = {test_s['minH']:.6e} при x = {test_s['xAtMinH']:.6f}")
        lines.append(f"max |ui-vi| = {test_s['maxAbsExactError']:.6e} при x = {test_s['xAtMaxAbsExactError']:.6f}")
        lines.append("")
        lines.append("Основная задача:")
        lines.append(f"n = {main_s['n']}, b - xn = {main_s['bMinusXn']:.6e}")
        lines.append(f"max |ОЛП| = {main_s['maxAbsOLP']:.6e}")
        lines.append(f"Общее число делений h = {main_s['totalDivisions']}")
        lines.append(f"Общее число удвоений h = {main_s['totalDoublings']}")
        lines.append(f"max h = {main_s['maxH']:.6e} при x = {main_s['xAtMaxH']:.6f}")
        lines.append(f"min h = {main_s['minH']:.6e} при x = {main_s['xAtMinH']:.6f}")

        self.summary_box.configure(state=tk.NORMAL)
        self.summary_box.delete("1.0", tk.END)
        self.summary_box.insert(tk.END, "\n".join(lines))
        self.summary_box.configure(state=tk.DISABLED)

    def fill_test_table(self) -> None:
        self._fill_current_table()

    def plot_test(self) -> None:
        data = self._read_result()["test"]["rows"]
        x = [r["x"] for r in data]
        vi = [r["v"][0] for r in data]
        ui = [r["uExact"] for r in data]

        fig, ax = plt.subplots(num="Тестовая задача", figsize=(9.5, 5.8))
        ax.plot(x, ui, label="u(x)", linewidth=2, color="#3b82f6")
        ax.plot(x, vi, label="v(x)", linestyle="--", color="#f97316")
        ax.set_xlabel("x")
        ax.set_ylabel("u(x)")
        ax.set_title("Сравнение решения тестовой задачи")
        ax.grid(True, alpha=0.3, linestyle="--")
        
        # Fixed legend location
        ax.legend(loc="upper right", framealpha=0.95, facecolor="white")
        
        fig.suptitle("Колесо мыши: zoom · ЛКМ + drag: pan", fontsize=9, color="#6b7280", y=0.98)
        self._attach_mouse_navigation(fig, [ax])
        plt.show()

    def plot_main(self) -> None:
        data = self._read_result()["main"]["rows"]
        x = [r["x"] for r in data]
        u = [r["v"][0] for r in data]
        du = [r["v"][1] if len(r["v"]) > 1 else 0.0 for r in data]

        fig, (ax1, ax2) = plt.subplots(2, 1, num="Основная задача", figsize=(9.5, 7.2), sharex=True)
        
        ax1.plot(x, u, color="#0d9488", label="Смещение u(x)")
        ax1.set_ylabel("u(x), см")
        ax1.grid(True, alpha=0.3, linestyle="--")
        ax1.legend(loc="upper right", framealpha=0.95, facecolor="white")
        ax1.set_title("Динамика положения груза")

        ax2.plot(x, du, color="#8b5cf6", label="Скорость u'(x)")
        ax2.set_xlabel("Время x, с")
        ax2.set_ylabel("u'(x), см/с")
        ax2.grid(True, alpha=0.3, linestyle="--")
        ax2.legend(loc="upper right", framealpha=0.95, facecolor="white")

        fig.suptitle("Колесо мыши: zoom · ЛКМ + drag: pan", fontsize=9, color="#6b7280", y=0.98)
        self._attach_mouse_navigation(fig, [ax1, ax2])
        plt.show()

    def plot_phase(self) -> None:
        data = self._read_result()["main"]["rows"]
        u = [r["v"][0] for r in data]
        du = [r["v"][1] if len(r["v"]) > 1 else 0.0 for r in data]

        fig, ax = plt.subplots(num="Фазовый портрет", figsize=(9.0, 6.2))
        ax.plot(u, du, color="#ef4444")
        ax.set_xlabel("Смещение u, см")
        ax.set_ylabel("Скорость u', см/с")
        ax.set_title("Фазовая траектория системы")
        ax.grid(True, alpha=0.3, linestyle="--")
        
        fig.suptitle("Колесо мыши: zoom · ЛКМ + drag: pan", fontsize=9, color="#6b7280", y=0.98)
        self._attach_mouse_navigation(fig, [ax])
        plt.show()

    def plot_experiments(self) -> None:
        data = self._read_result()["experiments"]
        if not data:
            messagebox.showinfo("Эксперименты", "Серии экспериментов отсутствуют")
            return

        fig, ax = plt.subplots(num="Параметрическое исследование", figsize=(10.0, 6.2))
        
        colors = ["#3b82f6", "#10b981", "#f59e0b", "#ef4444", "#8b5cf6", "#ec4899"]
        
        for idx, block in enumerate(data):
            rows = block["rows"]
            x = [r["x"] for r in rows]
            u = [r["v"][0] for r in rows]
            
            raw_name = block["problemName"]
            label = raw_name
            if "kStar_" in raw_name:
                val = raw_name.split("_")[-1]
                label = f"k* = {val} Н/см³"
            elif "c_" in raw_name:
                val = raw_name.split("_")[-1]
                label = f"c = {val} Нс/см²"

            color = colors[idx % len(colors)]
            ax.plot(x, u, label=label, color=color, linewidth=1.5)

        ax.set_xlabel("Время x, с")
        ax.set_ylabel("Смещение u(x), см")
        ax.set_title("Влияние нелинейности k* и демпфирования c")
        ax.grid(True, alpha=0.3, linestyle="--")
        ax.legend(fontsize=9, loc="upper right", framealpha=0.95, facecolor="white")
        
        fig.suptitle("Колесо мыши: zoom · ЛКМ + drag: pan", fontsize=9, color="#6b7280", y=0.98)
        self._attach_mouse_navigation(fig, [ax])
        plt.show()


if __name__ == "__main__":
    os.chdir(Path(__file__).resolve().parent.parent)
    app = LabUI()
    app.mainloop()
