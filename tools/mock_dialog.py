import sys
import tkinter as tk
from PIL import Image, ImageTk

path = sys.argv[1]
delay = float(sys.argv[2]) if len(sys.argv) > 2 else 1.0
scale = float(sys.argv[3]) if len(sys.argv) > 3 else 2 / 3  # 150%图→100%屏

root = tk.Tk()
root.attributes("-fullscreen", True)
root.attributes("-topmost", True)
root.configure(bg="white")


def show():
    img = Image.open(path)
    if abs(scale - 1.0) > 1e-6:
        img = img.resize((int(img.width * scale), int(img.height * scale)),
                         Image.LANCZOS)
    ph = ImageTk.PhotoImage(img)
    cv = tk.Canvas(root, width=root.winfo_screenwidth(),
                   height=root.winfo_screenheight(), bg="white",
                   highlightthickness=0)
    cv.pack()
    x = (root.winfo_screenwidth() - img.width) // 2
    y = (root.winfo_screenheight() - img.height) // 2
    cv.create_image(x, y, image=ph, anchor="nw")
    root._img = ph  # 防 GC
    cv.bind("<Button-1>", on_click)


def on_click(e):
    print(f"MOCK_CLICK x={e.x} y={e.y}", flush=True)
    root.destroy()


root.after(int(delay * 1000), show)
root.mainloop()
