"""
Axial Resolution Measurement — Thin launcher.

All application logic lives in the axial_app package.
"""

from axial_app.main import App


if __name__ == "__main__":
    app = App()
    app.resizable(True, True)
    app.mainloop()
