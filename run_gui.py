import tkinter as tk

from src.GUI.main_window import MainWindow
from src.GUI.analysis_scroll import install_analysis_scroll

install_analysis_scroll(MainWindow)


def main():
    root = tk.Tk()
    # A interface estava ocupando espaço demais em telas menores.
    # 80% mantém os controles legíveis e deixa a linha de comando do
    # Terminal visível/clicável sem alterar a lógica da máquina.
    root.tk.call("tk", "scaling", 0.80)
    MainWindow(root)
    root.mainloop()


if __name__ == "__main__":
    main()
