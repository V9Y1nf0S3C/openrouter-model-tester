#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Suppress macOS Tkinter warnings
import os
import sys
os.environ['TK_SILENCE_DEPRECATION'] = '1'

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import threading
import time
import json
from decimal import Decimal
from typing import List
from api_client import OpenRouterClient
from logging_utils import DualLogger


class CollapsibleFrame(ttk.Frame):
    """A collapsible/expandable frame widget."""
    
    def __init__(self, parent, text="", *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)
        
        self.is_expanded = tk.BooleanVar(value=True)
        
        # Header frame with toggle button
        self.header = ttk.Frame(self)
        self.header.grid(row=0, column=0, sticky="ew", padx=2, pady=2)
        
        self.toggle_btn = ttk.Button(
            self.header,
            text="▼ " + text,
            command=self._toggle,
            width=len(text) + 3
        )
        self.toggle_btn.pack(side="left", fill="x", expand=True)
        
        # Content frame
        self.content = ttk.Frame(self, relief="solid", borderwidth=1)
        self.content.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
        
        self.text = text
        # Reasoning control
        self.enable_reasoning_var = tk.BooleanVar(value=False)
        
    def _toggle(self):
        """Toggle the frame expansion."""
        if self.is_expanded.get():
            # Collapse
            self.content.grid_remove()
            self.toggle_btn.config(text="▶ " + self.text)
            self.is_expanded.set(False)
        else:
            # Expand
            self.content.grid()
            self.toggle_btn.config(text="▼ " + self.text)
            self.is_expanded.set(True)
    
    def get_content_frame(self):
        """Return the content frame for adding widgets."""
        return self.content


class OpenRouterGUI:
    """Main GUI application for OpenRouter model testing."""
    
    # Default LLM parameters
    DEFAULT_TEMP = 0.7
    DEFAULT_TOP_P = 0.95
    DEFAULT_TOP_K = 40
    DEFAULT_MAX_TOKENS = 1024
    
    # Default skip keywords
    DEFAULT_SKIP_KEYWORDS = "embedding,rerank,moderation,whisper,tts,vision-only"
    
    def __init__(self, root):
        self.root = root
        self.root.title("OpenRouter Model Tester")
        self.root.geometry("1400x950")

        # NEW: Configure macOS-compatible button style
        style = ttk.Style()
        if self.root.tk.call('tk', 'windowingsystem') == 'aqua':  # macOS only
            style.configure('TButton', padding=(0, 2))  # Reduce vertical padding
            
        # Create main canvas with scrollbar for vertical scrolling
        self.main_canvas = tk.Canvas(self.root, highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(self.root, orient="vertical", command=self.main_canvas.yview)
        self.scrollable_frame = ttk.Frame(self.main_canvas)
        
        # Configure scrollable region
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.main_canvas.configure(scrollregion=self.main_canvas.bbox("all"))
        )
        
        self.canvas_frame = self.main_canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.main_canvas.configure(yscrollcommand=self.scrollbar.set)
        
        # Bind canvas width to frame width for proper resizing
        self.main_canvas.bind('<Configure>', self._on_canvas_configure)
        
        # Pack canvas and scrollbar
        self.main_canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")
        
        # Bind mousewheel to canvas for scrolling
        self.main_canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        self.main_canvas.bind_all("<Button-4>", self._on_mousewheel)
        self.main_canvas.bind_all("<Button-5>", self._on_mousewheel)
        
        self.client = None
        self.logger = None
        self.available_models = []
        self.selected_models = []
        
        # Sorting variables
        self.model_costs = {}
        self.model_pricing = {}
        self.sort_by_cost_var = tk.BooleanVar(value=False)
        self.sort_cost_type_var = tk.StringVar(value="input")
        
        # Execution tracking
        self.execution_results = []
        self.usd_to_inr = 89.5
        
        # Session balance tracking
        self.initial_balance = None
        self.last_balance = None
        self.balance_check_count = 0
        
        # Cache for models
        self.models_loaded = False
        
        self._create_widgets()
        self._init_logger()
    
    def _on_canvas_configure(self, event):
        """Update the canvas window width when canvas is resized."""
        self.main_canvas.itemconfig(self.canvas_frame, width=event.width)
    
    def _on_mousewheel(self, event):
        """Handle mousewheel scrolling for Windows and Linux."""
        if event.num == 4:
            self.main_canvas.yview_scroll(-1, "units")
        elif event.num == 5:
            self.main_canvas.yview_scroll(1, "units")
        else:
            self.main_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
    
    def _create_widgets(self):
        """Create all GUI components."""
        
        # ===== API & PROXY CONFIGURATION (COLLAPSIBLE) =====
        api_proxy_collapsible = CollapsibleFrame(self.scrollable_frame, text="API & Proxy Configuration")
        api_proxy_collapsible.grid(row=0, column=0, columnspan=2, sticky="ew", padx=10, pady=5)
        api_proxy_content = api_proxy_collapsible.get_content_frame()
        api_proxy_content.columnconfigure(1, weight=1)
        
        # API Key section in api_proxy_content
        ttk.Label(api_proxy_content, text="API Key:").grid(row=0, column=0, sticky="w", padx=5, pady=5)

        # Frame for API key entry and show/hide button
        api_key_frame = ttk.Frame(api_proxy_content)
        api_key_frame.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        api_key_frame.columnconfigure(0, weight=1)

        self.api_key_var = tk.StringVar()
        self.api_key_entry = ttk.Entry(api_key_frame, textvariable=self.api_key_var, show="*", width=50)
        self.api_key_entry.grid(row=0, column=0, sticky="ew")

        # Show/Hide button
        self.show_api_key_btn = ttk.Button(api_key_frame, text="👁", width=3, command=self._toggle_api_key_visibility)
        self.show_api_key_btn.grid(row=0, column=1, padx=(5, 0))

        self.check_balance_btn = ttk.Button(api_proxy_content, text="Check Key Balance", command=self._check_key_balance)
        self.check_balance_btn.grid(row=0, column=2, padx=5, pady=5)

        self.balance_label = ttk.Label(api_proxy_content, text="Balance: Not checked", foreground="gray")
        self.balance_label.grid(row=0, column=3, padx=10, pady=5, sticky="w")

        
        # Proxy settings
        ttk.Label(api_proxy_content, text="Proxy:").grid(row=1, column=0, sticky="w", padx=5, pady=5)
        
        proxy_frame = ttk.Frame(api_proxy_content)
        proxy_frame.grid(row=1, column=1, columnspan=3, sticky="ew", padx=5, pady=5)
        
        self.proxy_enabled_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(proxy_frame, text="Route via Burp", variable=self.proxy_enabled_var).pack(side="left", padx=5)
        
        self.proxy_url_var = tk.StringVar(value="http://127.0.0.1:8080")
        ttk.Entry(proxy_frame, textvariable=self.proxy_url_var, width=30).pack(side="left", padx=5)
        
        self.verify_ssl_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(proxy_frame, text="Verify SSL", variable=self.verify_ssl_var).pack(side="left", padx=5)
        
        # ===== MODEL SELECTION (COLLAPSIBLE) =====
        model_collapsible = CollapsibleFrame(self.scrollable_frame, text="Model Selection")
        model_collapsible.grid(row=1, column=0, columnspan=2, sticky="nsew", padx=10, pady=5)
        model_content = model_collapsible.get_content_frame()
        model_content.columnconfigure(0, weight=1)
        model_content.columnconfigure(2, weight=1)
        model_content.rowconfigure(2, weight=1)
        
        # Model loading options
        load_options_frame = ttk.Frame(model_content)
        load_options_frame.grid(row=0, column=0, columnspan=4, sticky="ew", pady=(0, 5))
        
        self.show_pricing_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(load_options_frame, text="Show pricing", variable=self.show_pricing_var).pack(side="left", padx=5)
        
        ttk.Button(load_options_frame, text="Load Models", command=self._load_models).pack(side="left", padx=5)
        
        # Skip keywords
        ttk.Label(load_options_frame, text="Skip keywords:").pack(side="left", padx=(20, 5))
        self.skip_keywords_var = tk.StringVar(value=self.DEFAULT_SKIP_KEYWORDS)
        ttk.Entry(load_options_frame, textvariable=self.skip_keywords_var, width=40).pack(side="left", padx=5)
        
        self.skip_enabled_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(load_options_frame, text="Apply filter", variable=self.skip_enabled_var, 
                       command=self._apply_skip_filter).pack(side="left", padx=5)
        
        # Sorting options
        sort_frame = ttk.Frame(model_content)
        sort_frame.grid(row=1, column=0, columnspan=4, sticky="ew", pady=(0, 5))
        
        ttk.Checkbutton(sort_frame, text="Sort by", variable=self.sort_by_cost_var,
                       command=self._sort_available_models).pack(side="left", padx=5)
        
        ttk.Radiobutton(sort_frame, text="Input $", variable=self.sort_cost_type_var, value="input",
                       command=self._sort_available_models).pack(side="left", padx=2)
        
        ttk.Radiobutton(sort_frame, text="Context", variable=self.sort_cost_type_var, value="context",
                       command=self._sort_available_models).pack(side="left", padx=2)
        
        
            
                
        # Available models (left) - WITH HORIZONTAL SCROLL
        left_frame = ttk.Frame(model_content)
        left_frame.grid(row=2, column=0, sticky="nsew", padx=5)
        left_frame.rowconfigure(2, weight=1)
        left_frame.columnconfigure(0, weight=1)

        ttk.Label(left_frame, text="Available Models").grid(row=0, column=0, columnspan=2, sticky="w")

        self.search_var = tk.StringVar()
        self.search_var.trace("w", self._filter_models)
        ttk.Entry(left_frame, textvariable=self.search_var).grid(row=1, column=0, columnspan=2, sticky="ew", pady=5)

        # Use Text widget with larger size and better selection
        self.available_text = tk.Text(left_frame, width=80, height=15, font=("Courier", 12), 
                                     wrap=tk.NONE, cursor="hand2")
        self.available_text.grid(row=2, column=0, sticky="nsew")

        # Bind single click for selection and double-click for add
        self.available_text.bind("<Button-1>", self._on_available_click)
        self.available_text.bind("<Double-Button-1>", self._on_available_double_click)

        # Vertical scrollbar
        scroll1_v = ttk.Scrollbar(left_frame, orient="vertical", command=self.available_text.yview)
        scroll1_v.grid(row=2, column=1, sticky="ns")

        # Horizontal scrollbar
        scroll1_h = ttk.Scrollbar(left_frame, orient="horizontal", command=self.available_text.xview)
        scroll1_h.grid(row=3, column=0, sticky="ew")

        self.available_text.config(yscrollcommand=scroll1_v.set, xscrollcommand=scroll1_h.set)
        
        
        
        

        # Control buttons (middle)
        btn_frame = ttk.Frame(model_content)
        btn_frame.grid(row=2, column=1, padx=10)

        ttk.Button(btn_frame, text="Double click to Add →", command=self._add_models).pack(pady=5)
        ttk.Button(btn_frame, text="← Remove", command=self._remove_models).pack(pady=5)
        ttk.Button(btn_frame, text="Clear All", command=self._clear_selected).pack(pady=5)

        # Selected models (right) - WITH HORIZONTAL SCROLL
        right_frame = ttk.Frame(model_content)
        right_frame.grid(row=2, column=2, sticky="nsew", padx=5)
        right_frame.rowconfigure(2, weight=1)
        right_frame.columnconfigure(0, weight=1)

        ttk.Label(right_frame, text="Selected Models").grid(row=0, column=0, columnspan=2, sticky="w")
        self.selected_count_label = ttk.Label(right_frame, text="(0 selected)", foreground="#FF8C00")
        self.selected_count_label.grid(row=1, column=0, columnspan=2, sticky="w")

        # Match font size with available models
        self.selected_listbox = tk.Listbox(right_frame, selectmode=tk.EXTENDED, 
                                           width=40, height=15, font=("Courier", 12))
        self.selected_listbox.grid(row=2, column=0, sticky="nsew")

        # Vertical scrollbar
        scroll2_v = ttk.Scrollbar(right_frame, orient="vertical", command=self.selected_listbox.yview)
        scroll2_v.grid(row=2, column=1, sticky="ns")

        # Horizontal scrollbar
        scroll2_h = ttk.Scrollbar(right_frame, orient="horizontal", command=self.selected_listbox.xview)
        scroll2_h.grid(row=3, column=0, sticky="ew")

        self.selected_listbox.config(yscrollcommand=scroll2_v.set, xscrollcommand=scroll2_h.set)


        
        # ===== LLM PARAMETERS & PROMPTS (COLLAPSIBLE) =====
        params_prompts_collapsible = CollapsibleFrame(self.scrollable_frame, text="LLM Parameters & Prompts")
        params_prompts_collapsible.grid(row=2, column=0, columnspan=2, sticky="nsew", padx=10, pady=5)
        params_content = params_prompts_collapsible.get_content_frame()
        params_content.columnconfigure(0, weight=1)
        params_content.rowconfigure(2, weight=1)
        params_content.rowconfigure(4, weight=1)
        
        # LLM Parameters
        param_frame = ttk.LabelFrame(params_content, text="Parameters", padding=10)
        param_frame.grid(row=0, column=0, sticky="ew", padx=5, pady=5)
        
        ttk.Label(param_frame, text="Temperature:").grid(row=0, column=0, sticky="w")
        self.temp_var = tk.DoubleVar(value=self.DEFAULT_TEMP)
        ttk.Spinbox(param_frame, from_=0.0, to=2.0, increment=0.1, textvariable=self.temp_var, width=10).grid(row=0, column=1, padx=5, sticky="w")
        
        ttk.Label(param_frame, text="Top-p:").grid(row=0, column=2, sticky="w", padx=(20,0))
        self.top_p_var = tk.DoubleVar(value=self.DEFAULT_TOP_P)
        ttk.Spinbox(param_frame, from_=0.0, to=1.0, increment=0.05, textvariable=self.top_p_var, width=10).grid(row=0, column=3, padx=5, sticky="w")
        
        ttk.Label(param_frame, text="Top-k:").grid(row=0, column=4, sticky="w", padx=(20,0))
        self.top_k_var = tk.IntVar(value=self.DEFAULT_TOP_K)
        ttk.Spinbox(param_frame, from_=1, to=100, increment=1, textvariable=self.top_k_var, width=10).grid(row=0, column=5, padx=5, sticky="w")
        
        ttk.Label(param_frame, text="Max Tokens:").grid(row=0, column=6, sticky="w", padx=(20,0))
        self.max_tokens_var = tk.IntVar(value=self.DEFAULT_MAX_TOKENS)
        ttk.Spinbox(param_frame, from_=1, to=4096, increment=128, textvariable=self.max_tokens_var, width=10).grid(row=0, column=7, padx=5, sticky="w")
        
        # Reasoning checkbox
        self.enable_reasoning_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(param_frame, text="Enable Reasoning", 
                        variable=self.enable_reasoning_var).grid(row=0, column=8, padx=(20,0), sticky="w")
        
        ttk.Button(param_frame, text="Reset to Default", command=self._reset_parameters).grid(row=0, column=9, padx=(20,0))
        
        # Prompts
        ttk.Label(params_content, text="System Prompt:").grid(row=1, column=0, sticky="w", padx=5)
        self.system_prompt = scrolledtext.ScrolledText(params_content, height=5, width=80)
        self.system_prompt.grid(row=2, column=0, sticky="nsew", padx=5, pady=(0,10))
        
        default_system = """You are a school teacher."""
        self.system_prompt.insert("1.0", default_system)
        
        ttk.Label(params_content, text="User Prompt:").grid(row=3, column=0, sticky="w", padx=5)
        self.user_prompt = scrolledtext.ScrolledText(params_content, height=5, width=80)
        self.user_prompt.grid(row=4, column=0, sticky="nsew", padx=5)
        
        # ===== EXECUTION (COLLAPSIBLE) =====
        exec_collapsible = CollapsibleFrame(self.scrollable_frame, text="Execution & Logs")
        exec_collapsible.grid(row=3, column=0, columnspan=2, sticky="nsew", padx=10, pady=5)
        exec_content = exec_collapsible.get_content_frame()
        exec_content.columnconfigure(0, weight=1)
        exec_content.rowconfigure(2, weight=1)
        
        # Control buttons
        btn_container = ttk.Frame(exec_content)
        btn_container.grid(row=0, column=0, sticky="ew", pady=(0,10))
        
        self.run_btn = ttk.Button(btn_container, text="Run on Selected Models", command=self._run_models)
        self.run_btn.pack(side="left", padx=5)
        
        ttk.Button(btn_container, text="Clear Logs", command=self._clear_logs).pack(side="left", padx=5)
        
        ttk.Button(btn_container, text="Save Config", command=self._save_config).pack(side="left", padx=5)
        ttk.Button(btn_container, text="Load Config", command=self._load_config).pack(side="left", padx=5)
        
        self.status_label = ttk.Label(btn_container, text="Ready", foreground="green")
        self.status_label.pack(side="left", padx=20)
        
        # Logs - WITH HORIZONTAL SCROLL
        ttk.Label(exec_content, text="Logs:").grid(row=1, column=0, sticky="w")

        log_frame = ttk.Frame(exec_content)
        log_frame.grid(row=2, column=0, sticky="nsew")
        log_frame.rowconfigure(0, weight=1)
        log_frame.columnconfigure(0, weight=1)

        self.log_text = scrolledtext.ScrolledText(log_frame, height=35, width=80, 
                                                 state=tk.DISABLED, wrap=tk.NONE, font=("Courier", 11))
        self.log_text.grid(row=0, column=0, sticky="nsew")

        # Horizontal scrollbar (vertical is built into ScrolledText)
        log_scroll_h = ttk.Scrollbar(log_frame, orient="horizontal", command=self.log_text.xview)
        log_scroll_h.grid(row=1, column=0, sticky="ew")
        self.log_text.config(xscrollcommand=log_scroll_h.set)

        
        # Configure grid weights
        self.scrollable_frame.columnconfigure(0, weight=1)
        self.scrollable_frame.rowconfigure(1, weight=1)
        self.scrollable_frame.rowconfigure(2, weight=1)
        self.scrollable_frame.rowconfigure(3, weight=2)
        
        # Setup keyboard shortcuts
        self._setup_shortcuts()
        
    def _toggle_api_key_visibility(self):
        """Toggle API key visibility between masked and plain text."""
        if self.api_key_entry.cget("show") == "*":
            self.api_key_entry.config(show="")
            self.show_api_key_btn.config(text="🔒")
        else:
            self.api_key_entry.config(show="*")
            self.show_api_key_btn.config(text="👁")


    def _setup_shortcuts(self):
        """Setup keyboard shortcuts for better UX."""
        # Ctrl+A to select all in available models
        self.available_text.bind("<Control-a>", self._select_all_available)
        self.available_text.bind("<Command-a>", self._select_all_available)  # macOS
        
        # Enter key to add selected
        self.available_text.bind("<Return>", lambda e: self._add_models())

    def _select_all_available(self, event):
        """Select all models in available list."""
        self.available_text.tag_add("sel", "3.0", tk.END)  # Skip header (lines 1-2)
        return "break"  # Prevent default behavior
        
        
    def _reset_parameters(self):
        """Reset LLM parameters to default values."""
        self.temp_var.set(self.DEFAULT_TEMP)
        self.top_p_var.set(self.DEFAULT_TOP_P)
        self.top_k_var.set(self.DEFAULT_TOP_K)
        self.max_tokens_var.set(self.DEFAULT_MAX_TOKENS)
        
        self.log_text.config(state=tk.NORMAL)
        self.logger.log("Reset LLM parameters to default values")
        self.log_text.config(state=tk.DISABLED)
    

    def _save_config(self):
        """Save current configuration including API key to file."""
        try:
            file_path = filedialog.asksaveasfilename(
                defaultextension=".json",
                filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
                title="Save Configuration"
            )
            
            if not file_path:
                return
            
            api_key = self.api_key_var.get()
            
            config = {
                "api_key": api_key,
                "proxy_enabled": self.proxy_enabled_var.get(),
                "proxy_url": self.proxy_url_var.get(),
                "verify_ssl": self.verify_ssl_var.get(),
                "show_pricing": self.show_pricing_var.get(),
                "skip_keywords": self.skip_keywords_var.get(),
                "skip_enabled": self.skip_enabled_var.get(),
                "sort_enabled": self.sort_by_cost_var.get(),
                "sort_type": self.sort_cost_type_var.get(),
                "enable_reasoning": self.enable_reasoning_var.get(),
                "temperature": self.temp_var.get(),
                "top_p": self.top_p_var.get(),
                "top_k": self.top_k_var.get(),
                "max_tokens": self.max_tokens_var.get(),
                "system_prompt": self.system_prompt.get("1.0", tk.END).strip(),
                "user_prompt": self.user_prompt.get("1.0", tk.END).strip(),
                "selected_models": self.selected_models
            }
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2)
            
            messagebox.showinfo("Success", 
                f"Configuration saved to:\n{file_path}\n\n"
                f"API Key: {'Saved ✓' if api_key else 'Empty ✗'}\n"
                f"API Key Length: {len(api_key)} characters\n"
                f"Selected Models: {len(self.selected_models)}")
            
            self.log_text.config(state=tk.NORMAL)
            self.logger.log(f"Configuration saved to: {file_path}")
            self.logger.log(f"API key saved: {api_key[:8]}...{api_key[-4:]} ({len(api_key)} chars)" if api_key else "No API key saved")
            self.log_text.config(state=tk.DISABLED)
            
        except Exception as e:
            messagebox.showerror("Save Error", f"Failed to save configuration:\n{str(e)}")




    
    def _load_config(self):
        """Load configuration from file including API key."""
        try:
            file_path = filedialog.askopenfilename(
                filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
                title="Load Configuration"
            )
            
            if not file_path:
                return
            
            with open(file_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            if not isinstance(config, dict):
                raise ValueError("Invalid configuration format")
            
            # Load API key FIRST and verify
            api_key = str(config.get("api_key", "")).strip()
            if api_key:
                self.api_key_var.set(api_key)
                self.log_text.config(state=tk.NORMAL)
                self.logger.log(f"API key loaded: {api_key[:8]}...{api_key[-4:]} ({len(api_key)} chars)")
                self.log_text.config(state=tk.DISABLED)
            else:
                self.log_text.config(state=tk.NORMAL)
                self.logger.log("No API key found in config file", level="WARNING")
                self.log_text.config(state=tk.DISABLED)
            
            # Load boolean settings
            self.proxy_enabled_var.set(bool(config.get("proxy_enabled", False)))
            self.verify_ssl_var.set(bool(config.get("verify_ssl", False)))
            self.show_pricing_var.set(bool(config.get("show_pricing", False)))
            self.skip_enabled_var.set(bool(config.get("skip_enabled", True)))
            self.sort_by_cost_var.set(bool(config.get("sort_enabled", False)))
            self.enable_reasoning_var.set(bool(config.get("enable_reasoning", False)))
            
            # Load string settings with sanitization
            proxy_url = str(config.get("proxy_url", "http://127.0.0.1:8080"))
            if proxy_url.startswith(("http://", "https://")):
                self.proxy_url_var.set(proxy_url)
            
            skip_kw = str(config.get("skip_keywords", self.DEFAULT_SKIP_KEYWORDS))
            self.skip_keywords_var.set(skip_kw[:200])
            
            sort_type = str(config.get("sort_type", "input"))
            if sort_type in ["input", "context"]:
                self.sort_cost_type_var.set(sort_type)
            
            # Load numeric parameters with validation
            temp = float(config.get("temperature", self.DEFAULT_TEMP))
            self.temp_var.set(max(0.0, min(2.0, temp)))
            
            top_p = float(config.get("top_p", self.DEFAULT_TOP_P))
            self.top_p_var.set(max(0.0, min(1.0, top_p)))
            
            top_k = int(config.get("top_k", self.DEFAULT_TOP_K))
            self.top_k_var.set(max(1, min(100, top_k)))
            
            max_tokens = int(config.get("max_tokens", self.DEFAULT_MAX_TOKENS))
            self.max_tokens_var.set(max(1, min(4096, max_tokens)))
            
            # Load prompts
            system_prompt = str(config.get("system_prompt", ""))
            self.system_prompt.delete("1.0", tk.END)
            if system_prompt:
                self.system_prompt.insert("1.0", system_prompt[:5000])
            
            user_prompt = str(config.get("user_prompt", ""))
            self.user_prompt.delete("1.0", tk.END)
            if user_prompt:
                self.user_prompt.insert("1.0", user_prompt[:5000])
            
            # Load selected models
            selected = config.get("selected_models", [])
            if isinstance(selected, list):
                self.selected_models = [str(m) for m in selected[:100]]
                self.selected_listbox.delete(0, tk.END)
                for model in self.selected_models:
                    self.selected_listbox.insert(tk.END, model)
                self._update_selected_count()
            
            # Force refresh the API key display
            self.root.update_idletasks()
            
            messagebox.showinfo("Success", 
                f"Configuration loaded from:\n{file_path}\n\n"
                f"API Key: {'Loaded ✓' if api_key else 'Not found ✗'}\n"
                f"Selected Models: {len(self.selected_models)}")
            
            self.log_text.config(state=tk.NORMAL)
            self.logger.log(f"Configuration loaded successfully from: {file_path}")
            self.log_text.config(state=tk.DISABLED)
            
        except Exception as e:
            messagebox.showerror("Load Error", f"Failed to load configuration:\n{str(e)}")

    
    def _init_logger(self):
        """Initialize the dual logger."""
        self.log_text.config(state=tk.NORMAL)
        self.logger = DualLogger(text_widget=self.log_text)
        self.log_text.config(state=tk.DISABLED)
    
    def _init_client(self):
        """Initialize or reinitialize the API client."""
        api_key = self.api_key_var.get().strip()
        if not api_key:
            raise ValueError("API key is required")
        
        proxy_url = self.proxy_url_var.get() if self.proxy_enabled_var.get() else None
        verify_ssl = self.verify_ssl_var.get()
        
        self.client = OpenRouterClient(api_key=api_key, proxy_url=proxy_url, verify_ssl=verify_ssl)
    
    def _check_key_balance(self):
        """Check and display API key balance with percentage comparison."""
        try:
            self._init_client()
            key_info = self.client.get_key_info()
            
            limit = key_info.get("limit", 0)
            usage = key_info.get("usage", 0)
            
            limit_decimal = Decimal(str(limit))
            usage_decimal = Decimal(str(usage))
            remaining = limit_decimal - usage_decimal
            
            if limit_decimal > 0:
                percentage_remaining = (remaining / limit_decimal) * 100
                
                self.balance_check_count += 1
                
                if self.balance_check_count == 1:
                    self.initial_balance = remaining
                    self.last_balance = remaining
                    
                    self.balance_label.config(
                        text=f"Remaining: ${remaining:.7f} ({percentage_remaining:.2f}%)",
                        foreground="green"
                    )
                    
                    self.log_text.config(state=tk.NORMAL)
                    self.logger.log_key_balance(key_info)
                    self.logger.log("→ Initial balance recorded for session")
                    self.log_text.config(state=tk.DISABLED)
                else:
                    diff_from_last = self.last_balance - remaining
                    diff_from_initial = self.initial_balance - remaining
                    
                    pct_change_from_last = (diff_from_last / self.last_balance * 100) if self.last_balance > 0 else 0
                    pct_change_from_initial = (diff_from_initial / self.initial_balance * 100) if self.initial_balance > 0 else 0
                    
                    self.balance_label.config(
                        text=f"Remaining: ${remaining:.7f} ({percentage_remaining:.2f}%) | Δ Last: {pct_change_from_last:+.3f}% | Δ Start: {pct_change_from_initial:+.3f}%",
                        foreground="green"
                    )
                    
                    self.log_text.config(state=tk.NORMAL)
                    self.logger.log_key_balance(key_info)
                    self.logger.log(f"→ Δ since last: ${diff_from_last:.7f} ({pct_change_from_last:+.3f}%)")
                    self.logger.log(f"→ Δ since start: ${diff_from_initial:.7f} ({pct_change_from_initial:+.3f}%)")
                    self.log_text.config(state=tk.DISABLED)
                    
                    self.last_balance = remaining
            else:
                self.balance_label.config(
                    text=f"Remaining: ${remaining:.7f}",
                    foreground="green"
                )
                
                self.log_text.config(state=tk.NORMAL)
                self.logger.log_key_balance(key_info)
                self.log_text.config(state=tk.DISABLED)
                
        except Exception as e:
            self.balance_label.config(text=f"Error: {str(e)}", foreground="red")
            messagebox.showerror("Balance Error", str(e))
    
    def _apply_skip_filter(self):
        """Reapply skip filter when checkbox changes."""
        if self.models_loaded:
            self._display_available_models()
    
    def _should_skip_model(self, model_id: str) -> bool:
        """Check if model should be skipped based on keywords."""
        if not self.skip_enabled_var.get():
            return False
        
        keywords = [kw.strip().lower() for kw in self.skip_keywords_var.get().split(",") if kw.strip()]
        model_id_lower = model_id.lower()
        
        return any(keyword in model_id_lower for keyword in keywords)
    
    def _load_models(self):
        """Load available models from API (only once per session)."""
        if self.models_loaded and self.available_models:
            self.log_text.config(state=tk.NORMAL)
            self.logger.log(f"Using cached models ({len(self.available_models)} models)")
            self.log_text.config(state=tk.DISABLED)
            self._display_available_models()
            return
        
        try:
            self._init_client()
            self.status_label.config(text="Loading models...", foreground="orange")
            self.root.update()
            
            self.available_models = self.client.list_models(include_pricing=True)
            
            # Store pricing data
            self.model_pricing = {}
            for model in self.available_models:
                if "prompt_price" in model and "completion_price" in model:
                    self.model_pricing[model["id"]] = {
                        "input_price": model.get("prompt_price", 0),
                        "output_price": model.get("completion_price", 0)
                    }
            
            self.models_loaded = True
            self._display_available_models()
            
            self.log_text.config(state=tk.NORMAL)
            self.logger.log(f"Loaded {len(self.available_models)} models from API (cached)")
            self.log_text.config(state=tk.DISABLED)
            
            self.status_label.config(text=f"Loaded {len(self.available_models)} models", foreground="green")
            
        except Exception as e:
            self.status_label.config(text="Error loading models", foreground="red")
            messagebox.showerror("Load Models Error", str(e))
    
    def _display_available_models(self):
        """Display available models with aligned pricing."""
        if not self.models_loaded or not self.available_models:
            return
        
        self._filter_models()
    
    def _filter_models(self, *args):
        """Filter and display models with aligned columns."""
        if not self.models_loaded or not self.available_models:
            return
        
        search_text = self.search_var.get().lower()
        
        # Filter models
        filtered_models = []
        for model in self.available_models:
            if self._should_skip_model(model["id"]):
                continue
            
            if search_text:
                if search_text not in model["id"].lower() and search_text not in model["name"].lower():
                    continue
            
            filtered_models.append(model)
        
        # Sort if enabled
        if self.sort_by_cost_var.get():
            sort_type = self.sort_cost_type_var.get()
            
            def get_sort_key(model):
                if sort_type == "input":
                    return self.model_pricing.get(model["id"], {}).get("input_price", 0)
                elif sort_type == "context":
                    return model.get("context_length", 0)
                return 0
            
            filtered_models = sorted(filtered_models, key=get_sort_key, reverse=True)
        
        # Display with aligned columns
        self.available_text.config(state=tk.NORMAL)
        self.available_text.delete("1.0", tk.END)
        
        show_pricing = self.show_pricing_var.get()
        
        if show_pricing:
            # Header with Reasoning column
            header = f"{'Model ID':<55} {'Context':<10} {'In $/M':<10} {'Out $/M':<10} {'Rsn':<5}\n"
            self.available_text.insert(tk.END, header, "header")
            self.available_text.insert(tk.END, "-" * 90 + "\n", "header")
            
            # Model rows
            for model in filtered_models:
                model_id = model["id"][:53]
                ctx = model.get("context_length", 0)
                
                # Format context
                if ctx >= 1_000_000:
                    ctx_str = f"{ctx/1_000_000:.1f}M"
                elif ctx >= 1000:
                    ctx_str = f"{ctx/1000:.0f}K"
                else:
                    ctx_str = f"{ctx}"
                
                # Get pricing
                pricing = self.model_pricing.get(model["id"], {})
                in_price = pricing.get("input_price", 0)
                out_price = pricing.get("output_price", 0)
                
                # Check if reasoning model
                is_reasoning = self._is_reasoning_model(model["id"])
                rsn_indicator = "✓" if is_reasoning else "-"
                
                line = f"{model_id:<55} {ctx_str:<10} ${in_price:<9.3f} ${out_price:<9.3f} {rsn_indicator:<5}\n"
                self.available_text.insert(tk.END, line)
                    
                line_start = f"{self.available_text.index(tk.END)}-2l"
                line_end = f"{self.available_text.index(tk.END)}-1l"
                self.available_text.tag_add(model["id"], line_start, line_end)
        else:
            for model in filtered_models:
                self.available_text.insert(tk.END, model["id"] + "\n")
                line_start = f"{self.available_text.index(tk.END)}-2l"
                line_end = f"{self.available_text.index(tk.END)}-1l"
                self.available_text.tag_add(model["id"], line_start, line_end)
        
        self.available_text.tag_config("header", font=("Courier", 12, "bold"))
        self.available_text.config(state=tk.DISABLED)

    def _is_reasoning_model(self, model_id: str) -> bool:
        """Check if model supports reasoning."""
        reasoning_patterns = ['o1', 'o3', 'deepthink', 'reasoning', 'deepseek-r1', 'qwq']
        model_id_lower = model_id.lower()
        return any(pattern in model_id_lower for pattern in reasoning_patterns)



    
    
    def _sort_available_models(self):
        """Sort available models (uses cached data)."""
        if not self.models_loaded or not self.available_models:
            return
        
        self._display_available_models()
        
        if self.sort_by_cost_var.get():
            sort_type = self.sort_cost_type_var.get()
            sort_label = "input price" if sort_type == "input" else "context size"
            
            self.log_text.config(state=tk.NORMAL)
            self.logger.log(f"Sorted by {sort_label} (cached data)")
            self.log_text.config(state=tk.DISABLED)
    
    def _is_image_model(self, model_id: str) -> bool:
        """Check if model is image generation."""
        image_patterns = ['dalle', 'dall-e', 'stable-diffusion', 'midjourney', 'imagen',
                         'playground', 'flux', 'sdxl', 'sd-', '/image', 'ideogram', 'recraft', 'kolors', 'pixart']
        return any(pattern in model_id.lower() for pattern in image_patterns)
    
    def _update_selected_count(self):
        """Update selected models count."""
        count = len(self.selected_models)
        self.selected_count_label.config(text=f"({count} selected)", foreground="#FF8C00")
        
        if count > 0:
            self.status_label.config(text=f"{count} models selected", foreground="#FF8C00")
        else:
            self.status_label.config(text="Ready", foreground="green")
    

    def _on_available_click(self, event):
        """Handle single click to select line."""
        try:
            # Get clicked position
            index = self.available_text.index(f"@{event.x},{event.y}")
            line_num = int(index.split('.')[0])
            
            # Don't select header lines
            if line_num <= 2:
                return
            
            # Clear previous selection
            self.available_text.tag_remove("sel", "1.0", tk.END)
            
            # Select the clicked line
            self.available_text.tag_add("sel", f"{line_num}.0", f"{line_num}.end")
            self.available_text.mark_set(tk.INSERT, f"{line_num}.0")
            
        except:
            pass

    def _on_available_double_click(self, event):
        """Handle double-click to add model - extract from first column only."""
        try:
            index = self.available_text.index(f"@{event.x},{event.y}")
            line = self.available_text.get(f"{index} linestart", f"{index} lineend")
            
            # Skip header and separator lines
            if not line or line.startswith("Model ID") or line.startswith("-"):
                return
            
            # Extract model ID from first column ONLY (before first space)
            parts = line.split()
            if not parts:
                return
            
            model_id = parts[0].strip()  # First column only
            
            # Validate model ID format (should contain '/')
            if '/' not in model_id:
                return
            
            # Check if it's an image model
            if self._is_image_model(model_id):
                messagebox.showwarning("Blocked", f"Image model blocked: {model_id}")
                return
            
            # Add to selected if not already there
            if model_id and model_id not in self.selected_models:
                self.selected_models.append(model_id)
                self.selected_listbox.insert(tk.END, model_id)
                self._update_selected_count()
                
                self.log_text.config(state=tk.NORMAL)
                self.logger.log(f"Added model: {model_id}")
                self.log_text.config(state=tk.DISABLED)
        except Exception as e:
            self.log_text.config(state=tk.NORMAL)
            self.logger.log(f"Error adding model: {str(e)}", level="ERROR")
            self.log_text.config(state=tk.DISABLED)

    def _add_models(self):
        """Add selected models - extract from first column only."""
        try:
            # Check if there's a selection
            sel_ranges = self.available_text.tag_ranges(tk.SEL)
            if not sel_ranges:
                messagebox.showinfo("Info", 
                    "Select models by:\n"
                    "• Single-click a line to select it\n"
                    "• Shift+Click to select multiple lines\n"
                    "• Double-click to add directly\n"
                    "• Or use Ctrl+A to select all\n\n"
                    "Then click 'Add →' button")
                return
            
            # Get all selected text
            start, end = sel_ranges[0], sel_ranges[1]
            selected_text = self.available_text.get(start, end)
            
            added_count = 0
            blocked_count = 0
            blocked_models = []
            skipped_count = 0
            
            for line in selected_text.split("\n"):
                # Skip empty, header, and separator lines
                if not line.strip() or line.startswith("Model") or line.startswith("-"):
                    continue
                
                # Extract model ID from FIRST COLUMN ONLY (before first space)
                parts = line.split()
                if not parts:
                    continue
                
                model_id = parts[0].strip()  # First column only
                
                # Validate model ID format (should contain '/')
                if '/' not in model_id:
                    skipped_count += 1
                    continue
                
                # Check if it's an image model
                if self._is_image_model(model_id):
                    blocked_count += 1
                    blocked_models.append(model_id)
                    continue
                
                # Add to selected
                if model_id and model_id not in self.selected_models:
                    self.selected_models.append(model_id)
                    self.selected_listbox.insert(tk.END, model_id)
                    added_count += 1
            
            self._update_selected_count()
            
            # Show results
            if added_count > 0:
                self.log_text.config(state=tk.NORMAL)
                self.logger.log(f"Added {added_count} model(s)")
                self.log_text.config(state=tk.DISABLED)
            
            if blocked_count > 0:
                model_list = "\n".join([f"- {m}" for m in blocked_models[:5]])
                if blocked_count > 5:
                    model_list += f"\n... and {blocked_count - 5} more"
                
                messagebox.showwarning(
                    "Image Models Blocked",
                    f"Blocked {blocked_count} image model(s):\n\n{model_list}\n\n"
                    f"Added {added_count} chat/text model(s)."
                )
        
        except Exception as e:
            messagebox.showerror("Error", f"Failed to add models: {str(e)}")




    def _remove_models(self):
        """Remove selected models."""
        selection = self.selected_listbox.curselection()
        for idx in reversed(selection):
            model_id = self.selected_listbox.get(idx)
            self.selected_models.remove(model_id)
            self.selected_listbox.delete(idx)
        
        self._update_selected_count()
    
    def _clear_selected(self):
        """Clear all selected models."""
        self.selected_models.clear()
        self.selected_listbox.delete(0, tk.END)
        self._update_selected_count()
    
    def _clear_logs(self):
        """Clear logs."""
        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete("1.0", tk.END)
        self.log_text.config(state=tk.DISABLED)
    
    def _run_models(self):
        """Run chat requests."""
        if not self.api_key_var.get().strip():
            messagebox.showerror("Validation Error", "API key is required")
            return
        
        if not self.selected_models:
            messagebox.showerror("Validation Error", "Please select at least one model")
            return
        
        user_prompt = self.user_prompt.get("1.0", tk.END).strip()
        if not user_prompt:
            messagebox.showerror("Validation Error", "User prompt is required")
            return
        
        thread = threading.Thread(target=self._execute_models, daemon=True)
        thread.start()
    
    def _execute_models(self):
        """Execute chat requests on selected models."""
        try:
            self.run_btn.config(state=tk.DISABLED)
            self.status_label.config(text="Running...", foreground="orange")
            
            self._init_client()
            
            system_prompt = self.system_prompt.get("1.0", tk.END).strip()
            user_prompt = self.user_prompt.get("1.0", tk.END).strip()
            temperature = self.temp_var.get()
            top_p = self.top_p_var.get()
            top_k = self.top_k_var.get()
            max_tokens = self.max_tokens_var.get()
            
            self.execution_results = []
            
            self.log_text.config(state=tk.NORMAL)
            
            try:
                key_info = self.client.get_key_info()
                self.logger.log_key_balance(key_info)
            except:
                self.logger.log("Could not fetch initial balance", level="WARNING")
            
            self.logger.separator("=", 80)
            self.logger.log(f"Starting execution on {len(self.selected_models)} models")
            self.logger.log(f"Parameters: temp={temperature}, top_p={top_p}, top_k={top_k}, max_tokens={max_tokens}")
            self.logger.log_prompts(system_prompt, user_prompt)
            self.logger.separator("=", 80)
            self.log_text.config(state=tk.DISABLED)
            
            # Execute on each model
            for model_id in self.selected_models:
                start_time = time.time()
                
                try:
                    self.log_text.config(state=tk.NORMAL)
                    self.logger.model_header(model_id)
                    self.logger.log("Sending request...")
                    
                    response, usage = self.client.chat(
                        model_id=model_id,
                        system_prompt=system_prompt,
                        user_prompt=user_prompt,
                        temperature=temperature,
                        top_p=top_p,
                        top_k=top_k,
                        max_tokens=max_tokens,
                        enable_reasoning=self.enable_reasoning_var.get() 
                    )
                    
                    execution_time = time.time() - start_time
                    
                    cost_details = usage.get("cost_details", {})
                    self.model_costs[model_id] = {
                        "input_cost": float(cost_details.get("upstream_inference_prompt_cost", 0)),
                        "output_cost": float(cost_details.get("upstream_inference_completions_cost", 0))
                    }
                    
                    cost_usd = Decimal(str(usage.get("cost", 0)))
                    
                    # Check if context window was exceeded (cost but no/empty response)
                    if cost_usd > 0 and (not response or len(response.strip()) < 10):
                        self.logger.log("⚠️  WARNING: Cost incurred but response is empty/incomplete!", level="WARNING")
                        self.logger.log("⚠️  Possible cause: Context window exceeded or max_tokens too low", level="WARNING")
                        
                        # Get model context window
                        for model in self.available_models:
                            if model["id"] == model_id:
                                ctx_window = model.get("context_length", 0)
                                prompt_tokens = usage.get("prompt_tokens", 0)
                                self.logger.log(f"   Model context: {ctx_window:,} tokens | Your prompt used: {prompt_tokens:,} tokens", level="WARNING")
                                self.logger.log(f"   Suggestion: Reduce prompt length or increase max_tokens (current: {max_tokens})", level="WARNING")
                                break
                    
                    self.execution_results.append({
                        "model": model_id,
                        "total_tokens": usage.get("total_tokens", 0),
                        "prompt_tokens": usage.get("prompt_tokens", 0),
                        "completion_tokens": usage.get("completion_tokens", 0),
                        "cost_usd": cost_usd,
                        "input_cost_usd": Decimal(str(cost_details.get("upstream_inference_prompt_cost", 0))),
                        "output_cost_usd": Decimal(str(cost_details.get("upstream_inference_completions_cost", 0))),
                        "execution_time": execution_time
                    })
                    
                    self.logger.log_usage(usage, execution_time)
                    self.logger.separator("-", 80)
                    self.logger.log("Response:")
                    self.logger.log(response if response else "(Empty response)")
                    self.logger.separator("-", 80)
                    self.log_text.config(state=tk.DISABLED)
                    
                except Exception as e:
                    execution_time = time.time() - start_time
                    self.log_text.config(state=tk.NORMAL)
                    self.logger.log(f"ERROR: {str(e)} (took {execution_time:.2f}s)", level="ERROR")
                    
                    # Store failed execution
                    self.execution_results.append({
                        "model": f"{model_id} (FAILED)",
                        "total_tokens": 0,
                        "prompt_tokens": 0,
                        "completion_tokens": 0,
                        "cost_usd": Decimal("0"),
                        "input_cost_usd": Decimal("0"),
                        "output_cost_usd": Decimal("0"),
                        "execution_time": execution_time
                    })
                    
                    self.logger.separator("-", 80)
                    self.log_text.config(state=tk.DISABLED)
            
            self.log_text.config(state=tk.NORMAL)
            
            total_cost = sum(r.get("cost_usd", Decimal("0")) for r in self.execution_results)
            
            self.logger.separator("=", 80)
            self.logger.log(f"Total Cost: ${total_cost:.7f} USD")
            self.logger.log(f"Total Cost: ₹{(total_cost * Decimal(str(self.usd_to_inr))):.4f} INR")
            
            self.logger.log_detailed_summary_table(self.execution_results, self.usd_to_inr)
            
            self.logger.separator("=", 80)
            self.logger.log("Execution completed")
            self.logger.log("Tip: Use 'Check Key Balance' to verify")
            self.logger.separator("=", 80)
            self.log_text.config(state=tk.DISABLED)
            
            self.status_label.config(text="Completed", foreground="green")
            
        except Exception as e:
            self.log_text.config(state=tk.NORMAL)
            self.logger.log(f"FATAL ERROR: {str(e)}", level="ERROR")
            self.log_text.config(state=tk.DISABLED)
            self.status_label.config(text="Error", foreground="red")
            messagebox.showerror("Execution Error", str(e))
        
        finally:
            self.run_btn.config(state=tk.NORMAL)


def main():
    root = tk.Tk()
    app = OpenRouterGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()
