import main
import ttkbootstrap as tb
from tkinter import filedialog
from tkinter import *
import threading

class GUI(tb.Window):
    def __init__(self):
        super().__init__
        self.thread = None
        self.initUI()
    
    def initUI(self):
        root = tb.Window(title='Monster Siren Downloader', themename='darkly')
        root.geometry('1024x500')

        root.columnconfigure(0, weight = 3)
        root.columnconfigure(1, weight = 1)
        root.rowconfigure(0, weight = 2)
        root.rowconfigure(1, weight = 1)

        aestheticFrame = tb.Frame(root)
        aestheticFrame.columnconfigure(0, weight = 1)
        aestheticFrame.rowconfigure(0, weight = 2)
        aestheticFrame.rowconfigure(1, weight = 1)
        aestheticFrame.grid(row = 0, column = 0)

        interfaceFrame = tb.Frame(root)
        interfaceFrame.columnconfigure(0, weight = 1)
        interfaceFrame.rowconfigure(0, weight = 1)
        interfaceFrame.rowconfigure(1, weight = 1)
        interfaceFrame.rowconfigure(2, weight = 1)
        interfaceFrame.grid(row = 0, column = 1)

        progressBar = tb.Meter(aestheticFrame, bootstyle='primary', amounttotal=100, amountused=0, textright='%', subtextstyle='primary')
        progressBar.grid(row = 0,column = 0, pady = 50)

        indicatorBar = tb.Progressbar(aestheticFrame, bootstyle='info', mode = 'indeterminate', length=200)

        fileDialogBtn = tb.Button(interfaceFrame, bootstyle = 'primary', text='Select downloading folder or enter below', command=lambda: self.dirDialog(selectedPath))
        fileDialogBtn.grid(row = 0, column = 0)

        selectedPath = tb.Entry(interfaceFrame, bootstyle = 'info', width = 40)
        selectedPath.grid(row = 1, column = 0, pady=10)

        runBtn = tb.Button(interfaceFrame, bootstyle = 'primary', text='Start download', command=lambda: self.run(selectedPath.get(), progressBar, indicatorBar))
        runBtn.grid(row = 2,column = 0, pady = 100, sticky='s')

        root.mainloop()


    def on_closing(self):
        if self.thread is not None and self.thread.is_alive():
            self.thread.join()
        self.destroy()
        return
    
    def dirDialog(self, widget = ''):
        dir = filedialog.askdirectory(mustexist=True)
        if widget != '':
            widget.delete(0, END)
            widget.insert(0, dir)
        return dir

    def indicatorBarOn(self, indicator):
        indicator.grid(row=1, column = 0)
        indicator.start()

    def run(self, dir, bar, indicator):
        if dir == '':
            return
        thread = threading.Thread(target=main.main, args=(dir, bar, indicator))
        bar.configure(amountused = 0)
        self.indicatorBarOn(indicator)
        thread.start()
        self.thread = thread
        return

if __name__ == '__main__':
    ui = GUI()