"""Entrada da GUI. A instalação de analysis_scroll modifica a montagem visual da aba Análise; não altera o protocolo do motor."""

import tkinter as tk

from src.GUI.main_window import MainWindow
from src.GUI.analysis_scroll import install_analysis_scroll

install_analysis_scroll(MainWindow)


## O QUE FAZ: Ponto de entrada da aplicação: cria a janela principal e inicia o ciclo de eventos do Tkinter.
def main():
    root = tk.Tk()
    # Escala normal (100%). O espaço do Terminal é resolvido no próprio layout.
    root.tk.call("tk", "scaling", 1.0)
    MainWindow(root)
    root.mainloop()


if __name__ == "__main__":
    main()
