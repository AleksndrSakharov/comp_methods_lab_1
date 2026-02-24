import json
import os
import subprocess
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

import matplotlib.pyplot as plt


class LabUI(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Лабораторная 1 — Методы вычислений")
        self.geometry("980x700")

        self.project_root = Path(__file__).resolve().parent.parent
        self.default_input = self.project_root / "input_examples" / "default_input.json"
        self.default_output = self.project_root / "output"

        self.input_path_var = tk.StringVar(value=str(self.default_input))
        self.output_dir_var = tk.StringVar(value=str(self.default_output))
        self.solver_path_var = tk.StringVar(value=self._default_solver_path())

        self._build_ui()

    def _default_solver_path(self) -> str:
        return str(self.project_root / "build" / "lab1_solver.exe")

    def _build_ui(self) -> None:
        top = ttk.Frame(self)
        top.pack(fill=tk.X, padx=10, pady=10)

        ttk.Label(top, text="Solver executable:").grid(row=0, column=0, sticky="w")
        ttk.Entry(top, textvariable=self.solver_path_var, width=95).grid(row=0, column=1, padx=8)
        ttk.Button(top, text="...", command=self.pick_solver).grid(row=0, column=2)

        ttk.Label(top, text="Input JSON:").grid(row=1, column=0, sticky="w", pady=(8, 0))
        ttk.Entry(top, textvariable=self.input_path_var, width=95).grid(row=1, column=1, padx=8, pady=(8, 0))
        ttk.Button(top, text="...", command=self.pick_input).grid(row=1, column=2, pady=(8, 0))

        ttk.Label(top, text="Output dir:").grid(row=2, column=0, sticky="w", pady=(8, 0))
        ttk.Entry(top, textvariable=self.output_dir_var, width=95).grid(row=2, column=1, padx=8, pady=(8, 0))
        ttk.Button(top, text="...", command=self.pick_output).grid(row=2, column=2, pady=(8, 0))

        actions = ttk.Frame(self)
        actions.pack(fill=tk.X, padx=10, pady=6)
        ttk.Button(actions, text="1) Запустить расчёт", command=self.run_solver).pack(side=tk.LEFT)
        ttk.Button(actions, text="2) Графики тестовой", command=self.plot_test).pack(side=tk.LEFT, padx=6)
        ttk.Button(actions, text="3) Графики основной", command=self.plot_main).pack(side=tk.LEFT, padx=6)
        ttk.Button(actions, text="4) Фазовый портрет", command=self.plot_phase).pack(side=tk.LEFT, padx=6)
        ttk.Button(actions, text="5) Эксперименты (k*, c)", command=self.plot_experiments).pack(side=tk.LEFT, padx=6)

        self.summary_box = tk.Text(self, height=16, wrap=tk.WORD)
        self.summary_box.pack(fill=tk.BOTH, expand=False, padx=10, pady=8)

        table_frame = ttk.Frame(self)
        table_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

        self.table = ttk.Treeview(table_frame, columns=(
            "i", "x", "vi", "v2i", "delta", "olp", "h", "c1", "c2", "ue", "err"
        ), show="headings")
        for name, text in [
            ("i", "i"), ("x", "xi"), ("vi", "vi"), ("v2i", "v2i"), ("delta", "vi-v2i"),
            ("olp", "ОЛП"), ("h", "hi"), ("c1", "C1"), ("c2", "C2"), ("ue", "ui"), ("err", "|ui-vi|")
        ]:
            self.table.heading(name, text=text)
            self.table.column(name, width=86, stretch=False)

        scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.table.yview)
        self.table.configure(yscrollcommand=scrollbar.set)
        self.table.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    def pick_solver(self) -> None:
        path = filedialog.askopenfilename(filetypes=[("Executable", "*.exe"), ("All files", "*.*")])
        if path:
            self.solver_path_var.set(path)

    def pick_input(self) -> None:
        path = filedialog.askopenfilename(filetypes=[("JSON", "*.json")])
        if path:
            self.input_path_var.set(path)

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
        solver = Path(self.solver_path_var.get())
        input_json = Path(self.input_path_var.get())
        output_dir = Path(self.output_dir_var.get())

        if not solver.exists():
            messagebox.showerror("Ошибка", f"Не найден solver: {solver}")
            return
        if not input_json.exists():
            messagebox.showerror("Ошибка", f"Не найден input JSON: {input_json}")
            return

        output_dir.mkdir(parents=True, exist_ok=True)
        cmd = [str(solver), str(input_json), str(output_dir)]
        try:
            completed = subprocess.run(cmd, check=True, capture_output=True, text=True)
        except subprocess.CalledProcessError as ex:
            messagebox.showerror("Ошибка запуска", ex.stderr or ex.stdout or str(ex))
            return

        self.show_summary(completed.stdout)
        self.fill_test_table()
        messagebox.showinfo("Готово", f"Расчёт выполнен. Результаты: {output_dir}")

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
        lines.append(f"max|ОЛП| = {test_s['maxAbsOLP']:.6e}")
        lines.append(f"делений = {test_s['totalDivisions']}, удвоений = {test_s['totalDoublings']}")
        lines.append(f"max h = {test_s['maxH']:.6e} при x = {test_s['xAtMaxH']:.6f}")
        lines.append(f"min h = {test_s['minH']:.6e} при x = {test_s['xAtMinH']:.6f}")
        lines.append(f"max|ui-vi| = {test_s['maxAbsExactError']:.6e} при x = {test_s['xAtMaxAbsExactError']:.6f}")
        lines.append("")
        lines.append("Основная задача:")
        lines.append(f"n = {main_s['n']}, b - xn = {main_s['bMinusXn']:.6e}")
        lines.append(f"max|ОЛП| = {main_s['maxAbsOLP']:.6e}")
        lines.append(f"делений = {main_s['totalDivisions']}, удвоений = {main_s['totalDoublings']}")
        lines.append(f"max h = {main_s['maxH']:.6e} при x = {main_s['xAtMaxH']:.6f}")
        lines.append(f"min h = {main_s['minH']:.6e} при x = {main_s['xAtMinH']:.6f}")

        self.summary_box.delete("1.0", tk.END)
        self.summary_box.insert(tk.END, "\n".join(lines))

    def fill_test_table(self) -> None:
        for item in self.table.get_children():
            self.table.delete(item)

        data = self._read_result()
        for row in data["test"]["rows"]:
            v = row["v"][0] if row["v"] else 0.0
            v2 = row["v2"][0] if row["v2"] else 0.0
            d = row["delta"][0] if row["delta"] else 0.0
            self.table.insert("", tk.END, values=(
                row["i"],
                f"{row['x']:.6f}",
                f"{v:.6f}",
                f"{v2:.6f}",
                f"{d:.3e}",
                f"{row['olp']:.3e}",
                f"{row['h']:.3e}",
                row["c1"],
                row["c2"],
                f"{row.get('uExact', 0.0):.6f}",
                f"{row.get('absExactError', 0.0):.3e}",
            ))

    def plot_test(self) -> None:
        data = self._read_result()["test"]["rows"]
        x = [r["x"] for r in data]
        vi = [r["v"][0] for r in data]
        ui = [r["uExact"] for r in data]

        plt.figure("Тестовая задача")
        plt.plot(x, ui, label="Точное решение", linewidth=2)
        plt.plot(x, vi, label="Приближенное RK4", linestyle="--")
        plt.xlabel("x")
        plt.ylabel("u(x)")
        plt.grid(True)
        plt.legend()
        plt.show()

    def plot_main(self) -> None:
        data = self._read_result()["main"]["rows"]
        x = [r["x"] for r in data]
        u = [r["v"][0] for r in data]
        du = [r["v"][1] if len(r["v"]) > 1 else 0.0 for r in data]

        fig, (ax1, ax2) = plt.subplots(2, 1, num="Основная задача", figsize=(9, 7), sharex=True)
        ax1.plot(x, u)
        ax1.set_ylabel("u(x), см")
        ax1.grid(True)

        ax2.plot(x, du)
        ax2.set_xlabel("x, c")
        ax2.set_ylabel("u'(x), см/с")
        ax2.grid(True)
        plt.show()

    def plot_phase(self) -> None:
        data = self._read_result()["main"]["rows"]
        u = [r["v"][0] for r in data]
        du = [r["v"][1] if len(r["v"]) > 1 else 0.0 for r in data]

        plt.figure("Фазовый портрет")
        plt.plot(u, du)
        plt.xlabel("u, см")
        plt.ylabel("u', см/с")
        plt.grid(True)
        plt.show()

    def plot_experiments(self) -> None:
        data = self._read_result()["experiments"]
        if not data:
            messagebox.showinfo("Эксперименты", "Серии экспериментов отсутствуют")
            return

        plt.figure("Влияние k* и c", figsize=(10, 6))
        for block in data:
            rows = block["rows"]
            x = [r["x"] for r in rows]
            u = [r["v"][0] for r in rows]
            plt.plot(x, u, label=block["problemName"])

        plt.xlabel("x, c")
        plt.ylabel("u(x), см")
        plt.grid(True)
        plt.legend(fontsize=8)
        plt.show()


if __name__ == "__main__":
    os.chdir(Path(__file__).resolve().parent.parent)
    app = LabUI()
    app.mainloop()
