"""tkinter 图形界面"""

import os
import glob
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from parser import parse_filename, parse_csv
from processor import process_file
from exporter import export_to_excel


class App:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("无人机动力系统拉力测试数据处理")
        self.root.geometry("700x550")
        self.root.resizable(True, True)

        self.input_dir = tk.StringVar()
        self.output_file = tk.StringVar()
        self.sigma = tk.DoubleVar(value=2.5)
        self.min_samples = tk.IntVar(value=3)
        self.csv_files = []
        self._build_ui()

    def _build_ui(self):
        # 样式
        frame_pad = {"padx": 10, "pady": 5}
        label_width = 14

        # --- 输入目录 ---
        f1 = ttk.Frame(self.root)
        f1.pack(fill="x", **frame_pad)
        ttk.Label(f1, text="CSV 目录：", width=label_width).pack(side="left")
        ttk.Entry(f1, textvariable=self.input_dir).pack(side="left", fill="x", expand=True)
        ttk.Button(f1, text="浏览...", command=self._browse_input).pack(side="left", padx=(5, 0))

        # --- 输出文件 ---
        f2 = ttk.Frame(self.root)
        f2.pack(fill="x", **frame_pad)
        ttk.Label(f2, text="输出文件：", width=label_width).pack(side="left")
        ttk.Entry(f2, textvariable=self.output_file).pack(side="left", fill="x", expand=True)
        ttk.Button(f2, text="浏览...", command=self._browse_output).pack(side="left", padx=(5, 0))

        # --- 参数 ---
        f3 = ttk.Frame(self.root)
        f3.pack(fill="x", **frame_pad)
        ttk.Label(f3, text="σ 系数：", width=label_width).pack(side="left")
        spin = ttk.Spinbox(f3, textvariable=self.sigma, from_=0.5, to=5.0, increment=0.5, width=8)
        spin.pack(side="left")
        ttk.Label(f3, text="  (异常值 σ 阈值)").pack(side="left")
        ttk.Label(f3, text="  最少样本数：").pack(side="left", padx=(20, 0))
        ttk.Spinbox(f3, textvariable=self.min_samples, from_=2, to=20, increment=1, width=8).pack(side="left")

        # --- 文件列表 ---
        f4 = ttk.Frame(self.root)
        f4.pack(fill="both", expand=True, **frame_pad)
        ttk.Label(f4, text="CSV 文件列表：").pack(anchor="w")
        self.file_listbox = tk.Listbox(f4, height=6)
        self.file_listbox.pack(fill="both", expand=True)

        # --- 进度 ---
        f5 = ttk.Frame(self.root)
        f5.pack(fill="x", **frame_pad)
        self.progress = ttk.Progressbar(f5, mode="determinate")
        self.progress.pack(fill="x")

        # --- 状态 ---
        f6 = ttk.Frame(self.root)
        f6.pack(fill="x", **frame_pad)
        self.status_text = tk.Text(f6, height=6, state="disabled", wrap="word")
        self.status_text.pack(fill="both", expand=True)
        scrollbar = ttk.Scrollbar(self.status_text)
        scrollbar.pack(side="right", fill="y")
        self.status_text.config(yscrollcommand=scrollbar.set)
        scrollbar.config(command=self.status_text.yview)

        # --- 按钮 ---
        f7 = ttk.Frame(self.root)
        f7.pack(fill="x", **frame_pad)
        ttk.Button(f7, text="扫描文件", command=self._scan_files).pack(side="left", padx=(0, 10))
        self.run_btn = ttk.Button(f7, text="开始处理", command=self._start_process)
        self.run_btn.pack(side="left")

        # 默认输出路径
        self.output_file.set(os.path.join(os.path.expanduser("~"), "Desktop", "力效测试汇总.xlsx"))

    def _browse_input(self):
        path = filedialog.askdirectory(title="选择 CSV 文件目录")
        if path:
            self.input_dir.set(path)
            self._scan_files()

    def _browse_output(self):
        path = filedialog.asksaveasfilename(
            title="保存输出文件",
            defaultextension=".xlsx",
            filetypes=[("Excel 文件", "*.xlsx")],
        )
        if path:
            self.output_file.set(path)

    def _scan_files(self):
        """扫描目录中的 CSV 文件并更新列表"""
        d = self.input_dir.get()
        if not d or not os.path.isdir(d):
            return
        self.csv_files = sorted(glob.glob(os.path.join(d, "*.csv")))
        self.file_listbox.delete(0, "end")
        for f in self.csv_files:
            self.file_listbox.insert("end", os.path.basename(f))
        self._log(f"找到 {len(self.csv_files)} 个 CSV 文件")

    def _log(self, msg: str):
        """输出日志到状态区"""
        self.status_text.config(state="normal")
        self.status_text.insert("end", msg + "\n")
        self.status_text.see("end")
        self.status_text.config(state="disabled")

    def _start_process(self):
        if not self.csv_files:
            messagebox.showwarning("提示", "请先选择 CSV 目录并扫描文件")
            return
        if not self.output_file.get():
            messagebox.showwarning("提示", "请先指定输出文件路径")
            return

        self.run_btn.config(state="disabled")
        self.progress["maximum"] = len(self.csv_files)
        self.progress["value"] = 0
        self._log("=" * 50)
        self._log("开始处理...")

        thread = threading.Thread(target=self._process_all, daemon=True)
        thread.start()

    def _process_all(self):
        sigma = self.sigma.get()
        min_samples = self.min_samples.get()
        all_results = []

        for i, filepath in enumerate(self.csv_files):
            filename = os.path.basename(filepath)
            try:
                file_info = parse_filename(filepath)
                metadata, data = parse_csv(filepath)
                result = process_file(filepath, metadata, data,
                                      sigma=sigma, min_samples=min_samples)
                all_results.append({
                    "filename": filename,
                    "file_info": file_info,
                    "metadata": metadata,
                    "pwm_result": result,
                })
                status = "OK" if result else "跳过（无有效稳态段）"
                self._log(f"[{i+1}/{len(self.csv_files)}] {filename} → {status}")
            except Exception as e:
                self._log(f"[{i+1}/{len(self.csv_files)}] {filename} → 出错: {e}")

            self.root.after(0, self._update_progress, i + 1)

        # 导出
        try:
            export_to_excel(all_results, self.output_file.get())
            self._log(f"\n导出完成: {self.output_file.get()}")
        except Exception as e:
            self._log(f"\n导出出错: {e}")

        self.root.after(0, self._on_done)

    def _update_progress(self, value):
        self.progress["value"] = value

    def _on_done(self):
        self.progress["value"] = self.progress["maximum"]
        self.run_btn.config(state="normal")
        self._log("处理完成！")
        messagebox.showinfo("完成", f"共处理 {len(self.csv_files)} 个文件\n输出: {self.output_file.get()}")
