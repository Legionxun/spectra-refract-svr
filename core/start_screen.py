# core.start_screen.py
import time
from tkinter import Canvas, NW, BOTH
from PIL import Image, ImageTk
from .utils import resource_path

class StartScreen:
    def __init__(self, rootMsct, root):
        self.rootMsct = rootMsct
        self.root = root

    def showWelcome(self):
        sw, sh = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
        self.root.overrideredirect(True)
        self.root.attributes("-alpha", 1)
        x, y = (sw - 600) / 2, (sh - 200) / 2
        self.root.geometry("700x200+%d+%d" % (x, y))

        canvas = Canvas(self.root, width=700, height=200, highlightthickness=0, bd=0)
        canvas.pack(fill=BOTH, expand=True)

        pil_image = Image.open(resource_path('./img/welcome.jpg'))
        pil_image = pil_image.resize((700, 200))
        bg_image = ImageTk.PhotoImage(pil_image)
        canvas.bg_image = bg_image
        canvas.create_image(0, 0, anchor=NW, image=bg_image)
        canvas.create_text(350,
                           100,
                           text='Welcome to OptiSVR Spectral Refractive Index Prediction System',
                           font=('Microsoft YaHei', 16),
                           fill='yellow')

    def closeWelcome(self):
        for i in range(2):
            self.rootMsct.attributes("-alpha", 0)
            time.sleep(1)
        self.rootMsct.attributes("-alpha", 1)
        self.root.destroy()