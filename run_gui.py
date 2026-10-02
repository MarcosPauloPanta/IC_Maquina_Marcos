import tkinter as tk

from src.GUI.main_window import MainWindow
from src.GUI.analysis_scroll import install_analysis_scroll

install_analysis_scroll(MainWindow)


def main():
    root = tk.Tk()
    # Escala normal do sistema. O problema de espaço do Terminal
    # é resolvido pelo layout da janela, não reduzindo toda a GUI.
    root.tk.call("tk", "scaling", 1.0)
    MainWindow(root)
    root.mainloop()


if __name__ == "__main__":
    main()
