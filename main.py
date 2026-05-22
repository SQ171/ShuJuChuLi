"""无人机动力系统拉力测试数据处理 — 程序入口"""

import tkinter as tk
from gui import App


def main():
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
