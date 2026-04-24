import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
import os
import builtins
from browser_agent import BrowserAgent

class AgentUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Vision Browser Agent - KDP Edition")
        self.root.geometry("720x600")
        
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky="nsew")
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        # Task Input
        ttk.Label(main_frame, text="Task Description:").grid(row=0, column=0, sticky="w", pady=2)
        self.task_text = tk.Text(main_frame, height=4, width=70)
        self.task_text.grid(row=1, column=0, columnspan=2, sticky="ew", pady=5)
        self.task_text.insert('1.0', "Fill Module 1, SAVE as draft. Then fill Module 2.")

        # URL Input
        ttk.Label(main_frame, text="Starting URL:").grid(row=2, column=0, sticky="w", pady=2)
        self.url_var = tk.StringVar(value="https://kdp.amazon.com/marketing/manager")
        ttk.Entry(main_frame, textvariable=self.url_var, width=60).grid(row=2, column=1, sticky="w", pady=2)

        # Profile Input
        ttk.Label(main_frame, text="Chrome Profile Folder (e.g. Profile 2):").grid(row=3, column=0, sticky="w", pady=2)
        self.profile_var = tk.StringVar(value="Default")
        ttk.Entry(main_frame, textvariable=self.profile_var, width=20).grid(row=3, column=1, sticky="w", pady=2)

        # Log Output
        ttk.Label(main_frame, text="Activity Log:").grid(row=4, column=0, sticky="w", pady=(10,2))
        self.log_area = tk.Text(main_frame, height=15, width=80, state="disabled", bg="#f0f0f0")
        self.log_area.grid(row=5, column=0, columnspan=2, sticky="nsew")
        
        # Buttons
        btn_frame = ttk.Frame(main_frame)
        btn_frame.grid(row=6, column=0, columnspan=2, pady=10)
        
        self.start_btn = ttk.Button(btn_frame, text="▶ START AGENT", command=self.start_agent)
        self.start_btn.pack(side="left", padx=5)
        
        ttk.Button(btn_frame, text="Clear Log", command=self.clear_log).pack(side="left", padx=5)

    def log(self, message, tag=None):
        def _log():
            self.log_area.config(state="normal")
            self.log_area.insert("end", f"[{threading.current_thread().name}] {message}\n")
            self.log_area.see("end")
            self.log_area.config(state="disabled")
        self.root.after(0, _log)

    def clear_log(self):
        self.log_area.config(state="normal")
        self.log_area.delete('1.0', 'end')
        self.log_area.config(state="disabled")

    def start_agent(self):
        task = self.task_text.get('1.0', 'end').strip()
        url = self.url_var.get().strip()
        profile = self.profile_var.get().strip()
        
        self.start_btn.config(state="disabled")
        threading.Thread(target=self._run_agent, args=(task, url, profile), daemon=True, name="Agent").start()

    def _run_agent(self, task, url, profile):
        try:
            # Setup logging redirection
            original_print = builtins.print
            builtins.print = lambda *args, **kwargs: self.log(" ".join(map(str, args)))
            
            agent = BrowserAgent(log_callback=self.log)
            agent.chrome_profile_dir = profile
            agent.run_task(task, url)
            
            self.log("✅ Session finished.")
        except Exception as e:
            self.log(f"✗ ERROR: {e}")
        finally:
            self.start_btn.after(0, lambda: self.start_btn.config(state="normal"))

    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    app = AgentUI()
    app.run()
