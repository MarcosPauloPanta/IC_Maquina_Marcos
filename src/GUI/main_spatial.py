from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from src.GUI.main_window import MainWindow as BaseMainWindow
from src.GUI.spatial_map import SpatialMap


class SpatialMainWindow(BaseMainWindow):
    """Versão da interface com a aba experimental Mapa Espacial.

    A janela original continua intacta. Esta classe apenas adiciona a nova
    aba e corrige a convenção visual do JOG do eixo X.
    """

    def _build(self):
        super()._build()
        self._add_spatial_map_tab()

    def _find_notebook(self, parent):
        for child in parent.winfo_children():
            if isinstance(child, ttk.Notebook):
                return child
            found = self._find_notebook(child)
            if found is not None:
                return found
        return None

    def _add_spatial_map_tab(self):
        notebook = self._find_notebook(self.root)
        if notebook is None:
            raise RuntimeError("Não foi possível localizar as abas da interface.")

        self.spatial_tab = ttk.Frame(notebook, padding=0)
        notebook.add(self.spatial_tab, text="Mapa Espacial")
        self.spatial_map = SpatialMap(self.spatial_tab, self._colors)

    def _jog_press(self, axis, direction):
        # Convenção mecânica atual:
        # X- físico aponta para fora do motor, ao contrário de Y- e Z-.
        # Portanto, somente no JOG de X invertemos o sinal enviado ao Arduino.
        if axis == "X":
            direction = -direction
        super()._jog_press(axis, direction)

    def toggle_dark_mode(self):
        super().toggle_dark_mode()
        if hasattr(self, "spatial_map"):
            self.spatial_map.refresh_theme()


def main():
    root = tk.Tk()
    SpatialMainWindow(root)
    root.mainloop()


if __name__ == "__main__":
    main()
