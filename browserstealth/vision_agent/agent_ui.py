import sys
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog, simpledialog
import threading
import time
import os
import json
import builtins
from datetime import datetime
from browser_agent import BrowserAgent

# --- PHILLIP: SUPERVISOR DISABLED ---
# from supervisor_agent import supervisor
# -----------------------------------

class AgentUI:
    """GUI for controlling the vision-based browser agent"""

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Vision Browser Agent")
        self.root.geometry("720x500")
        self.root.resizable(True, True)

        self.agent = None
        self.agent_thread = None
        self.is_running = False
        self.verification_submitted = False
        self.waiting_for_verification = False
        self.task_rows = []
        self.file_rows = []

        self._saved_tasks_file = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), 'saved_tasks.json'
        )

        self.setup_ui()
        self._load_saved_tasks_list()

    def setup_ui(self):
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        outer = ttk.Frame(self.root)
        outer.grid(row=0, column=0, sticky="nsew")
        outer.columnconfigure(0, weight=1)
        outer.rowconfigure(0, weight=1)

        canvas = tk.Canvas(outer, highlightthickness=0)
        vsb = ttk.Scrollbar(outer, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=vsb.set)
        canvas.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")

        main_frame = ttk.Frame(canvas, padding="6")
        canvas_window = canvas.create_window((0, 0), window=main_frame, anchor="nw")

        def _on_frame_configure(event):
            canvas.configure(scrollregion=canvas.bbox("all"))

        def _on_canvas_configure(event):
            canvas.itemconfig(canvas_window, width=event.width)

        main_frame.bind("<Configure>", _on_frame_configure)
        canvas.bind("<Configure>", _on_canvas_configure)

        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)

        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(6, weight=1)

        ttk.Label(main_frame, text="Vision Browser Agent", font=("Arial", 11, "bold")).grid(row=0, column=0, pady=(0, 4))

        config_frame = ttk.LabelFrame(main_frame, text="Configuration", padding="5")
        config_frame.grid(row=1, column=0, sticky="ew", pady=(0, 4))
        config_frame.columnconfigure(1, weight=1)

        saved_row = ttk.Frame(config_frame)
        saved_row.grid(row=0, column=0, columnspan=3, sticky="ew", pady=(0, 6))
        saved_row.columnconfigure(1, weight=1)
        ttk.Label(saved_row, text="Saved Tasks:").grid(row=0, column=0, sticky="w", padx=(0, 8))
        self.saved_var = tk.StringVar()
        self.saved_combo = ttk.Combobox(saved_row, textvariable=self.saved_var, state="readonly", width=35)
        self.saved_combo.grid(row=0, column=1, sticky="ew", padx=(0, 6))
        self.saved_combo.bind("<<ComboboxSelected>>", lambda e: self.load_saved_task())
        ttk.Button(saved_row, text="Save", command=self.save_task, width=8).grid(row=0, column=2, padx=(0, 4))
        ttk.Button(saved_row, text="Delete", command=self.delete_saved_task, width=8).grid(row=0, column=3)

        builder_frame = ttk.LabelFrame(config_frame, text="Task Builder", padding="4")
        builder_frame.grid(row=1, column=0, columnspan=3, sticky="ew", pady=(0, 4))
        builder_frame.columnconfigure(0, weight=1)
        self.synopsis_text = tk.Text(builder_frame, height=1, wrap="word")
        self.synopsis_text.grid(row=0, column=0, sticky="ew", pady=(0, 2))
        self.synopsis_text.insert('1.0', "e.g. Search Google for the best CRM tools, visit the top 3 results and collect the pricing from each site")
        self.synopsis_text.config(foreground="grey")
        def _synopsis_focus_in(e):
            if self.synopsis_text.cget('foreground') == 'grey':
                self.synopsis_text.delete('1.0', 'end')
                self.synopsis_text.config(foreground='black')
        def _synopsis_focus_out(e):
            if not self.synopsis_text.get('1.0', 'end').strip():
                self.synopsis_text.insert('1.0', "e.g. Search Google for the best CRM tools, visit the top 3 results and collect the pricing from each site")
                self.synopsis_text.config(foreground='grey')
        self.synopsis_text.bind('<FocusIn>', _synopsis_focus_in)
        self.synopsis_text.bind('<FocusOut>', _synopsis_focus_out)
        self.generate_btn = ttk.Button(builder_frame, text="✨ Generate Task", command=self.generate_task)
        self.generate_btn.grid(row=1, column=0, sticky="w")

        ttk.Label(config_frame, text="URL:").grid(row=2, column=0, sticky="w", padx=(0, 6), pady=2)
        self.url_var = tk.StringVar()
        ttk.Entry(config_frame, textvariable=self.url_var).grid(row=2, column=1, columnspan=2, sticky="ew", pady=2)

        ttk.Label(config_frame, text="Task:").grid(row=3, column=0, sticky="nw", padx=(0, 6), pady=2)
        self.task_text = tk.Text(config_frame, height=2, wrap="word")
        self.task_text.grid(row=3, column=1, columnspan=2, sticky="ew", pady=2)

        cred_frame = ttk.LabelFrame(config_frame, text="Login Credentials", padding="4")
        cred_frame.grid(row=4, column=0, columnspan=3, sticky="ew", pady=(0, 4))
        cred_frame.columnconfigure(1, weight=1)
        ttk.Label(cred_frame, text="Username / Email:").grid(row=0, column=0, sticky="w", padx=(0, 8), pady=2)
        self.username_var = tk.StringVar()
        ttk.Entry(cred_frame, textvariable=self.username_var).grid(row=0, column=1, sticky="ew", pady=2)
        ttk.Label(cred_frame, text="Password:").grid(row=1, column=0, sticky="w", padx=(0, 8), pady=2)
        self.password_var = tk.StringVar()
        ttk.Entry(cred_frame, textvariable=self.password_var, show="*").grid(row=1, column=1, sticky="ew", pady=2)

        ttk.Label(config_frame, text="Model:").grid(row=5, column=0, sticky="w", padx=(0, 8), pady=3)
        self.model_var = tk.StringVar(value="mimo-v2-omni")
        model_options = ["mimo-v2-omni", "kimi-k2.6"]
        ttk.Combobox(config_frame, textvariable=self.model_var, values=model_options, width=25).grid(row=5, column=1, sticky="w", pady=3)

        chrome_frame = ttk.LabelFrame(config_frame, text="Chrome Settings (optional)", padding="4")
        chrome_frame.grid(row=6, column=0, columnspan=3, sticky="ew", pady=(4, 0))
        chrome_frame.columnconfigure(1, weight=1)

        ttk.Label(chrome_frame, text="Chrome Binary:").grid(row=0, column=0, sticky="w", padx=(0, 8), pady=2)
        self.chrome_binary_var = tk.StringVar()
        chrome_bin_row = ttk.Frame(chrome_frame)
        chrome_bin_row.grid(row=0, column=1, columnspan=2, sticky="ew")
        chrome_bin_row.columnconfigure(0, weight=1)
        ttk.Entry(chrome_bin_row, textvariable=self.chrome_binary_var).grid(row=0, column=0, sticky="ew")
        ttk.Button(chrome_bin_row, text="Browse", width=7, command=lambda: self.chrome_binary_var.set(filedialog.askopenfilename(filetypes=[("Executable", "*.exe"), ("All", "*.*")]) or self.chrome_binary_var.get())).grid(row=0, column=1, padx=(4, 0))

        ttk.Label(chrome_frame, text="User Data Dir:").grid(row=1, column=0, sticky="w", padx=(0, 8), pady=2)
        self.chrome_data_var = tk.StringVar()
        data_row = ttk.Frame(chrome_frame)
        data_row.grid(row=1, column=1, columnspan=2, sticky="ew")
        data_row.columnconfigure(0, weight=1)
        ttk.Entry(data_row, textvariable=self.chrome_data_var).grid(row=0, column=0, sticky="ew")
        ttk.Button(data_row, text="Browse", width=7, command=lambda: self.chrome_data_var.set(filedialog.askdirectory() or self.chrome_data_var.get())).grid(row=0, column=1, padx=(4, 0))

        ttk.Label(chrome_frame, text="Profile Dir:").grid(row=2, column=0, sticky="w", padx=(0, 8), pady=2)
        self.chrome_profile_var = tk.StringVar()
        ttk.Entry(chrome_frame, textvariable=self.chrome_profile_var).grid(row=2, column=1, columnspan=2, sticky="ew", pady=2)

        files_frame = ttk.LabelFrame(config_frame, text="Upload Files (optional)", padding="4")
        files_frame.grid(row=7, column=0, columnspan=3, sticky="ew", pady=(4, 0))
        files_frame.columnconfigure(0, weight=1)
        self.files_list_frame = ttk.Frame(files_frame)
        self.files_list_frame.grid(row=0, column=0, sticky="ew")
        self.files_list_frame.columnconfigure(0, weight=1)
        ttk.Button(files_frame, text="+ Add File", command=self.add_file_row).grid(row=1, column=0, sticky="w", pady=(4, 0))

        self.verif_frame = ttk.LabelFrame(main_frame, text="Human Verification Required", padding="5")
        self.verif_label = ttk.Label(self.verif_frame, text="", wraplength=700, justify="left")
        self.verif_label.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 6))
        self.verif_entry = ttk.Entry(self.verif_frame, width=40)
        self.verif_entry.grid(row=1, column=0, sticky="ew", padx=(0, 6))
        self.verif_entry.bind("<Return>", lambda e: self.submit_verification())
        ttk.Button(self.verif_frame, text="Submit", command=self.submit_verification).grid(row=1, column=1)
        self.verif_frame.columnconfigure(0, weight=1)

        btn_frame = ttk.Frame(main_frame)
        btn_frame.grid(row=3, column=0, sticky="ew", pady=(0, 8))
        self.start_btn = ttk.Button(btn_frame, text="▶ Start Agent", command=self.start_agent, width=18)
        self.start_btn.pack(side="left", padx=(0, 8))
        self.stop_btn = ttk.Button(btn_frame, text="⏹ Stop", command=self.stop_agent, width=12, state="disabled")
        self.stop_btn.pack(side="left", padx=(0, 8))
        ttk.Button(btn_frame, text="Clear Log", command=self.clear_log, width=10).pack(side="left")

        self.status_var = tk.StringVar(value="Ready")
        status_bar = ttk.Frame(main_frame, relief="sunken")
        status_bar.grid(row=4, column=0, sticky="ew", pady=(0, 6))
        self.status_label = ttk.Label(status_bar, textvariable=self.status_var, anchor="w")
        self.status_label.pack(fill="x", padx=4, pady=2)

        results_frame = ttk.LabelFrame(main_frame, text="Results", padding="4")
        results_frame.grid(row=5, column=0, sticky="ew", pady=(0, 4))
        results_frame.columnconfigure(0, weight=1)
        self.results_header = ttk.Label(results_frame, text="No results yet", font=("Arial", 9, "italic"))
        self.results_header.grid(row=0, column=0, sticky="w", pady=(0, 2))
        self.results_text = scrolledtext.ScrolledText(results_frame, height=2, wrap="word", state="disabled")
        self.results_text.grid(row=1, column=0, sticky="ew")
        ttk.Button(results_frame, text="Copy", command=self.copy_results, width=8).grid(row=2, column=0, sticky="e", pady=(4, 0))

        log_frame = ttk.LabelFrame(main_frame, text="Log", padding="4")
        log_frame.grid(row=6, column=0, sticky="nsew", pady=(0, 4))
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        main_frame.rowconfigure(6, weight=1)

        self.log_text = scrolledtext.ScrolledText(log_frame, height=10, wrap="word", state="disabled", font=("Courier", 8))
        self.log_text.grid(row=0, column=0, sticky="nsew")

        self.log_text.tag_configure("success", foreground="#00aa00")
        self.log_text.tag_configure("error", foreground="#cc0000")
        self.log_text.tag_configure("action", foreground="#0055cc", font=("Courier", 8, "bold"))
        self.log_text.tag_configure("reasoning", foreground="#888800")
        self.log_text.tag_configure("info", foreground="#555555")

    def generate_task(self):
        synopsis = self.synopsis_text.get('1.0', 'end').strip()
        if not synopsis or synopsis.startswith('e.g.'):
            messagebox.showwarning("Empty", "Describe what you want first.")
            return
        model = self.model_var.get().strip() or "gemini-3-flash"
        self.generate_btn.config(state="disabled", text="Generating...")
        self.root.update()

        def _run():
            try:
                import requests
                import json
                import re
                system_prompt = """You are a browser automation task planner. Respond in this exact JSON format: {"task": "...", "url": "..."}"""
                user_msg = f"Convert this into an agent task:\n\n{synopsis}"
                api_key = os.getenv('OPENCODE_API_KEY')
                if not api_key: raise ValueError("OPENCODE_API_KEY not found in environment variables")
                payload = { "model": model, "messages": [ {"role": "system", "content": system_prompt}, {"role": "user", "content": user_msg} ], "temperature": 0.3, "max_tokens": 1024 }
                response = requests.post("https://opencode.ai/zen/go/v1/chat/completions", headers={'Content-Type': 'application/json', 'Authorization': f'Bearer {api_key}'}, json=payload, timeout=30)
                response.raise_for_status()
                msg = response.json()['choices'][0]['message']
                text = msg.get('content', '').strip()
                task, url = text, ''
                m = re.search(r'\{.*\}', text, re.DOTALL)
                if m:
                    try:
                        data = json.loads(m.group(0))
                        task = data.get('task', text)
                        url = data.get('url', '')
                    except json.JSONDecodeError: pass
                def _apply():
                    self.task_text.delete('1.0', 'end')
                    self.task_text.insert('1.0', task)
                    if url: self.url_var.set(url)
                    self.generate_btn.config(state="normal", text="✨ Generate Task")
                self.root.after(0, _apply)
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("Error", str(e)))
                self.root.after(0, lambda: self.generate_btn.config(state="normal", text="✨ Generate Task"))
        threading.Thread(target=_run, daemon=True).start()

    def add_file_row(self, path=""):
        var = tk.StringVar(value=path)
        row_idx = len(self.file_rows)
        row = ttk.Frame(self.files_list_frame)
        row.grid(row=row_idx, column=0, sticky="ew", pady=1)
        row.columnconfigure(0, weight=1)
        ttk.Entry(row, textvariable=var).grid(row=0, column=0, sticky="ew")
        ttk.Button(row, text="Browse", width=7, command=lambda v=var: v.set(filedialog.askopenfilename() or v.get())).grid(row=0, column=1, padx=(4, 0))
        ttk.Button(row, text="✕", width=3, command=lambda r=row, v=var: self._remove_file_row(r, v)).grid(row=0, column=2, padx=(2, 0))
        self.file_rows.append(var)

    def _remove_file_row(self, row_widget, var):
        row_widget.destroy()
        if var in self.file_rows: self.file_rows.remove(var)

    def _read_saved_tasks(self):
        if not os.path.exists(self._saved_tasks_file): return []
        with open(self._saved_tasks_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if isinstance(data, dict) and 'tasks' in data: return data['tasks']
            if isinstance(data, list): return data
            return []

    def _write_saved_tasks(self, tasks):
        with open(self._saved_tasks_file, 'w', encoding='utf-8') as f: json.dump({'tasks': tasks}, f, indent=2, ensure_ascii=False)

    def _load_saved_tasks_list(self):
        try:
            tasks = self._read_saved_tasks()
            names = [t.get('name', f'Task {i+1}') for i, t in enumerate(tasks)]
            self.saved_combo['values'] = names
        except Exception: pass

    def load_saved_task(self):
        try:
            name = self.saved_var.get()
            if not name: return
            tasks = self._read_saved_tasks()
            for t in tasks:
                if t.get('name') == name:
                    self.url_var.set(t.get('url', ''))
                    raw_tasks = t.get('tasks') or t.get('task') or ''
                    task_str = '\n'.join(raw_tasks) if isinstance(raw_tasks, list) else raw_tasks
                    asin = t.get('asin', '').strip()
                    if asin: task_str += f"\n\nASIN to apply: {asin} — on the 'Apply ASINs' page, enter this ASIN in the ASIN input field and click Apply."
                    self.task_text.delete('1.0', 'end')
                    self.task_text.insert('1.0', task_str)
                    self.model_var.set(t.get('model', 'gemini-3-flash'))
                    self.username_var.set(t.get('username', ''))
                    self.password_var.set(t.get('password', ''))
                    for widget in self.files_list_frame.winfo_children(): widget.destroy()
                    self.file_rows.clear()
                    for f in t.get('files', []):
                        if f: self.add_file_row(f)
                    if t.get('chrome_profile'): self.chrome_profile_var.set(t['chrome_profile'])
                    break
        except Exception as e: messagebox.showerror("Error", f"Could not load task: {e}")

    def save_task(self):
        name = simpledialog.askstring("Save Task", "Task name:", parent=self.root)
        if not name: return
        task = self.task_text.get('1.0', 'end').strip()
        url = self.url_var.get().strip()
        model = self.model_var.get()
        files = [v.get().strip() for v in self.file_rows if v.get().strip()]
        try: tasks = self._read_saved_tasks()
        except Exception: tasks = []
        tasks = [t for t in tasks if t.get('name') != name]
        username, password = self.username_var.get().strip(), self.password_var.get().strip()
        tasks.append({'name': name, 'url': url, 'task': task, 'model': model, 'files': files, 'username': username, 'password': password})
        self._write_saved_tasks(tasks)
        self._load_saved_tasks_list()
        self.saved_var.set(name)

    def delete_saved_task(self):
        name = self.saved_var.get()
        if not name: return
        if not messagebox.askyesno("Delete", f"Delete saved task '{name}'?"): return
        try:
            tasks = self._read_saved_tasks()
            tasks = [t for t in tasks if t.get('name') != name]
            self._write_saved_tasks(tasks)
        except Exception: pass
        self._load_saved_tasks_list(); self.saved_var.set('')

    def start_agent(self):
        task = self.task_text.get('1.0', 'end').strip()
        if not task:
            messagebox.showwarning("Missing Task", "Please enter a task.")
            return
        url = self.url_var.get().strip()
        model = self.model_var.get().strip() or "gemini-3-flash"
        self.start_btn.config(state="disabled")
        self.stop_btn.config(state="normal")
        self.is_running = True
        self.verification_submitted = False
        self.waiting_for_verification = False
        self.verif_entry.delete(0, 'end')
        self.verif_frame.grid_remove()
        self.update_status("Starting...", "blue")
        self.agent_thread = threading.Thread(target=self._run_agent_thread, args=(task, url, model), daemon=True)
        self.agent_thread.start()

    def stop_agent(self):
        self.is_running = False
        self.update_status("Saving draft & stopping...", "orange")
        if self.agent:
            try: self.agent.save_draft()
            except Exception: pass
            try: self.agent.close()
            except Exception: pass
        self.agent = None
        self.start_btn.config(state="normal")
        self.stop_btn.config(state="disabled")
        self.update_status("Stopped", "red")

    def _run_agent_thread(self, task, url, model):
        original_print = builtins.print
        def ui_print(*args, **kwargs):
            message = ' '.join(str(a) for a in args)
            tag = None
            if any(x in message for x in ["✓", "SUCCESS", "CONFIRMED", "completed"]): tag = "success"
            elif any(x in message for x in ["✗", "Error", "FAILED", "error"]): tag = "error"
            elif "Action:" in message: tag = "action"
            elif "Reasoning:" in message: tag = "reasoning"
            elif any(x in message for x in ["Navigating", "Analyzing", "Starting", "Planner", "Verifier"]): tag = "info"
            self.log(message, tag)
            # --- PHILLIP: SUPERVISOR LOGGING REMOVED ---
            # supervisor.log(message)
            # ------------------------------------------
            original_print(*args, **kwargs)
        builtins.print = ui_print

        try:
            # --- PHILLIP: REUSING YOUR CUSTOM LOG_CALLBACK ---
            self.agent = BrowserAgent(log_callback=ui_print)
            # -----------------------------------------------

            ui_username, ui_password = self.username_var.get().strip(), self.password_var.get().strip()
            if ui_username: self.agent.username = ui_username
            if ui_password: self.agent.password = ui_password

            binary, data_dir, profile = self.chrome_binary_var.get().strip(), self.chrome_data_var.get().strip(), self.chrome_profile_var.get().strip()
            if binary: self.agent.chrome_binary = binary
            if data_dir: self.agent.chrome_user_data_dir = data_dir
            if profile: self.agent.chrome_profile_dir = profile

            self.agent.upload_files = [v.get().strip() for v in self.file_rows if v.get().strip()]
            self.agent.start_browser()

            # --- PHILLIP: SUPERVISOR STARTUP REMOVED ---
            # supervisor.start()
            # ------------------------------------------

            self.update_status(f"Running with {model}...", "blue")
            if url:
                if not url.startswith(('http://', 'https://')): url = 'https://' + url
                self.log(f"Navigating to: {url}", "info")
                self.agent.driver.get(url)
                time.sleep(2)
                self.log("📋 Building semantic map & plan...", "info")
                # Using the new foolproof map logic
                self.agent.get_semantic_map()

            iteration = 0
            while iteration < self.agent.max_iterations and self.is_running:
                iteration += 1
                if self.waiting_for_verification:
                    while self.waiting_for_verification and not self.verification_submitted and self.is_running:
                        time.sleep(0.5); self.root.update()
                    if self.verification_submitted:
                        self.waiting_for_verification = False; self.verification_submitted = False
                        self.log("Resuming agent...", "info"); continue

                if self.agent is None: break
                screenshot_path = self.agent.take_screenshot(f"iter_{iteration:03d}.png")
                semantic_map = self.agent.get_semantic_map()
                
                # This calls your Vision AI with the new semantic map
                action = self.agent.vision.analyze_screenshot(screenshot_path, task, semantic_map=semantic_map)
                
                # Logging Seer output
                saw = action.get('screenshot_description', '') or action.get('reasoning', '')
                act = action.get('action', '?')
                self.log(f"👁️ SEES: {saw}", "info")
                self.log(f"➡️ NEXT: {act}", "info")

                if not self.is_running or self.agent is None: break
                result = self.agent.execute_action(action)
                if result is True or result == 'complete': break
                elif result is False: break
                time.sleep(2)

            self.update_status("Task Done", "green")
        except Exception as e:
            self.log(f"Agent error: {e}", "error")
            self.update_status("Error", "red")
        finally:
            builtins.print = original_print
            if self.agent:
                try: self.agent.close()
                except Exception: pass
            self.agent = None
            self.root.after(0, lambda: self.start_btn.config(state="normal"))
            self.root.after(0, lambda: self.stop_btn.config(state="disabled"))
            self.is_running = False

    def _show_verification_request(self, request_text):
        self.verif_label.config(text=request_text)
        self.verif_entry.delete(0, 'end')
        self.verif_frame.grid(row=2, column=0, sticky="ew", pady=(0, 8))
        self.root.after(0, self.verif_entry.focus_set)

    def submit_verification(self):
        value = self.verif_entry.get().strip()
        if not value: return
        self.verification_submitted = True
        self.waiting_for_verification = False
        self.verif_frame.grid_remove()

    def log(self, message, tag=None):
        def _append():
            self.log_text.config(state="normal")
            ts = datetime.now().strftime("%H:%M:%S")
            self.log_text.insert("end", f"[{ts}] {message}\n", tag or "")
            self.log_text.see("end")
            self.log_text.config(state="disabled")
        self.root.after(0, _append)

    def clear_log(self):
        self.log_text.config(state="normal")
        self.log_text.delete('1.0', 'end')
        self.log_text.config(state="disabled")

    def update_status(self, text, color="black"):
        def _update():
            self.status_var.set(text)
            self.status_label.config(foreground=color)
        self.root.after(0, _update)

    def show_result(self, text, header=""):
        def _show():
            if header: self.results_header.config(text=header)
            self.results_text.config(state="normal")
            self.results_text.delete('1.0', 'end')
            self.results_text.insert('1.0', text)
            self.results_text.config(state="disabled")
        self.root.after(0, _show)

    def copy_results(self):
        text = self.results_text.get('1.0', 'end').strip()
        if text: self.root.clipboard_clear(); self.root.clipboard_append(text); self.log("Results copied to clipboard.", "info")

    def run(self): self.root.mainloop()

if __name__ == "__main__":
    app = AgentUI()
    app.run()
