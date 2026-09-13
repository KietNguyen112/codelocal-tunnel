import os
import queue
import re
import sys
import threading
import time
import webbrowser
import subprocess
from typing import Optional
import tkinter as tk
from tkinter import messagebox
import customtkinter as ctk

from core.codelocal_client import CodeLocalDetector
from core.config_store import ConfigManager
from core.tunnel_runner import TunnelManager
from ui import theme
from ui.components import CardFrame, CopyableField, PasswordEntryWithToggle, StatusBadge


class MainWindow(ctk.CTk):
    """Main desktop application window for CodeLocal Tunnel Gateway."""

    def __init__(self):
        super().__init__()

        # Appearance & Base Window Setup
        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("blue")

        self.title("CodeLocal Tunnel Gateway")
        self.geometry("1120x780")
        self.minsize(900, 650)
        self.configure(fg_color=theme.BG_DARK)

        # Core Services
        self.config_mgr = ConfigManager()
        self.detector = CodeLocalDetector()
        self.tunnel_mgr = TunnelManager(
            status_callback=self._on_tunnel_status,
            log_callback=self._on_tunnel_log,
        )

        # State Variables
        self.current_lang = self.config_mgr.get("language", "vi")
        self.selected_mode = self.config_mgr.get("selected_mode", "cloudflare")  # "cloudflare" or "openai"
        self._ui_queue = queue.Queue()
        self._closing = False
        self._auto_scroll = True

        # Build Interface
        self._create_layout()
        self._load_saved_data()

        # Start Periodic Background Tasks
        self.after(100, self._process_ui_queue)
        self.after(500, self._check_codelocal_backend_loop)
        self.after(1000, self._update_uptime_loop)

        # Handle Window Close Gracefully
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def t(self, key: str) -> str:
        """Translate key to current language."""
        lang_dict = theme.I18N.get(self.current_lang, theme.I18N["vi"])
        return lang_dict.get(key, theme.I18N["vi"].get(key, key))

    # -------------------------------------------------------------------------
    # Layout Creation
    # -------------------------------------------------------------------------
    def _create_layout(self):
        """Build a real desktop shell instead of the old stacked dashboard."""
        self.grid_columnconfigure(0, weight=0, minsize=218)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self._build_sidebar()

        self.content_shell = ctk.CTkFrame(self, fg_color=theme.BG_DARK, corner_radius=0)
        self.content_shell.grid(row=0, column=1, sticky="nsew")
        self.content_shell.grid_columnconfigure(0, weight=1)
        self.content_shell.grid_rowconfigure(1, weight=1)
        self._build_header(parent=self.content_shell)

        self.page_host = ctk.CTkFrame(self.content_shell, fg_color="transparent", corner_radius=0)
        self.page_host.grid(row=1, column=0, sticky="nsew", padx=(0, 24), pady=(0, 8))
        self.page_host.grid_columnconfigure(0, weight=1)
        self.page_host.grid_rowconfigure(0, weight=1)

        self.pages = {}
        self.health_labels = {}
        self._build_overview_page()
        self._build_cloudflare_page()
        self._build_openai_page()
        self._build_diagnostics_page()
        self._build_activity_page()
        self._build_settings_page()
        self._build_footer(parent=self.content_shell)
        self._show_page("overview")

    def _build_sidebar(self):
        sidebar = ctk.CTkFrame(self, fg_color=theme.BG_SURFACE, corner_radius=0)
        sidebar.grid(row=0, column=0, sticky="nsew")
        sidebar.grid_rowconfigure(8, weight=1)
        brand = ctk.CTkFrame(sidebar, fg_color="transparent")
        brand.pack(fill="x", padx=18, pady=(22, 28))
        ctk.CTkLabel(brand, text="CODELOCAL", anchor="w", font=ctk.CTkFont(size=11, weight="bold"), text_color=theme.ACCENT_CYAN).pack(anchor="w")
        ctk.CTkLabel(brand, text="Tunnel Gateway", anchor="w", font=ctk.CTkFont(size=18, weight="bold"), text_color=theme.TEXT_PRIMARY).pack(anchor="w", pady=(2, 0))
        ctk.CTkLabel(brand, text="Local MCP connectivity", anchor="w", font=ctk.CTkFont(size=10), text_color=theme.TEXT_MUTED).pack(anchor="w", pady=(5, 0))
        self.nav_buttons = {}
        groups = [("WORKSPACE", [("overview", "Overview")]), ("CONNECTIONS", [("cloudflare", "Cloudflare"), ("openai", "OpenAI Secure")]), ("TOOLS", [("diagnostics", "Diagnostics"), ("activity", "Activity Log")]), ("SYSTEM", [("settings", "Settings")])]
        for group_name, items in groups:
            ctk.CTkLabel(sidebar, text=group_name, anchor="w", font=ctk.CTkFont(size=9, weight="bold"), text_color=theme.TEXT_MUTED).pack(fill="x", padx=18, pady=(7, 6))
            for page_id, label in items:
                btn = ctk.CTkButton(sidebar, text=label, anchor="w", height=36, fg_color="transparent", hover_color=theme.BG_SURFACE_ALT, text_color=theme.TEXT_SECONDARY, font=ctk.CTkFont(size=12, weight="bold"), corner_radius=5, command=lambda p=page_id: self._show_page(p))
                btn.pack(fill="x", padx=10, pady=1)
                self.nav_buttons[page_id] = btn
        status_box = ctk.CTkFrame(sidebar, fg_color=theme.BG_SURFACE_ALT, corner_radius=6)
        status_box.pack(fill="x", padx=12, pady=14)
        ctk.CTkLabel(status_box, text="BACKEND", anchor="w", font=ctk.CTkFont(size=9, weight="bold"), text_color=theme.TEXT_MUTED).pack(fill="x", padx=10, pady=(9, 2))
        self.backend_sidebar_label = ctk.CTkLabel(status_box, text=self.t("backend_offline"), anchor="w", font=ctk.CTkFont(size=10, weight="bold"), text_color=theme.COLOR_CONNECTING)
        self.backend_sidebar_label.pack(fill="x", padx=10, pady=(0, 9))

    def _show_page(self, page_id: str):
        if page_id not in self.pages:
            return
        for frame in self.pages.values():
            frame.grid_forget()
        self.pages[page_id].grid(row=0, column=0, sticky="nsew")
        self.current_page = page_id
        for name, btn in self.nav_buttons.items():
            btn.configure(fg_color=theme.BG_SURFACE_ALT if name == page_id else "transparent", text_color=theme.TEXT_PRIMARY if name == page_id else theme.TEXT_SECONDARY)
        if page_id == "cloudflare":
            self.selected_mode = "cloudflare"
            self._update_cf_preview_url()
        elif page_id == "openai":
            self.selected_mode = "openai"
            self._update_oa_preview_url()

    def _new_page(self, page_id, title, subtitle):
        page = ctk.CTkScrollableFrame(self.page_host, fg_color="transparent", scrollbar_button_color=theme.BORDER_SUBTLE, scrollbar_button_hover_color=theme.BORDER_FOCUS)
        page.grid_columnconfigure(0, weight=1)
        self.pages[page_id] = page
        head = ctk.CTkFrame(page, fg_color="transparent")
        head.pack(fill="x", padx=2, pady=(4, 18))
        ctk.CTkLabel(head, text=title, anchor="w", font=ctk.CTkFont(size=23, weight="bold"), text_color=theme.TEXT_PRIMARY).pack(anchor="w")
        ctk.CTkLabel(head, text=subtitle, anchor="w", font=ctk.CTkFont(size=11), text_color=theme.TEXT_MUTED).pack(anchor="w", pady=(4, 0))
        return page

    def _build_overview_page(self):
        page = self._new_page("overview", "Overview", "Live tunnel state, endpoint and the actions you use most")
        status = ctk.CTkFrame(page, fg_color=theme.BG_SURFACE, corner_radius=6, border_width=1, border_color=theme.BORDER_SUBTLE)
        status.pack(fill="x", pady=(0, 10))
        top = ctk.CTkFrame(status, fg_color="transparent")
        top.pack(fill="x", padx=18, pady=(16, 8))
        ctk.CTkLabel(top, text="TUNNEL STATUS", anchor="w", font=ctk.CTkFont(size=9, weight="bold"), text_color=theme.TEXT_MUTED).pack(side="left")
        self.status_badge = StatusBadge(top, initial_text=self.t("status_offline"), initial_color=theme.COLOR_OFFLINE)
        self.status_badge.pack(side="right")
        self.status_title_lbl = ctk.CTkLabel(top, text=self.t("status_title"), anchor="e", font=ctk.CTkFont(size=11), text_color=theme.TEXT_SECONDARY)
        self.status_title_lbl.pack(side="right", padx=(0, 12))
        self.status_detail_lbl = ctk.CTkLabel(status, text=self.t("status_detail_offline"), anchor="w", justify="left", font=ctk.CTkFont(size=12), text_color=theme.TEXT_SECONDARY)
        self.status_detail_lbl.pack(fill="x", padx=18, pady=(0, 12))
        self.uptime_lbl = ctk.CTkLabel(status, text=self.t("uptime") + " --:--:--", anchor="w", font=ctk.CTkFont(family="Consolas", size=10), text_color=theme.TEXT_MUTED)
        self.uptime_lbl.pack(fill="x", padx=18, pady=(0, 14))

        endpoint = ctk.CTkFrame(page, fg_color=theme.BG_SURFACE, corner_radius=6, border_width=1, border_color=theme.BORDER_SUBTLE)
        endpoint.pack(fill="x", pady=10)
        ctk.CTkLabel(endpoint, text="MCP ENDPOINT", anchor="w", font=ctk.CTkFont(size=9, weight="bold"), text_color=theme.TEXT_MUTED).pack(fill="x", padx=18, pady=(14, 5))
        self.public_url_field = CopyableField(endpoint, placeholder_text="Public MCP endpoint", readonly=True)
        self.public_url_field.pack(fill="x", padx=18, pady=(0, 16))

        actions = ctk.CTkFrame(page, fg_color="transparent")
        actions.pack(fill="x", pady=10)
        self.action_btn = ctk.CTkButton(actions, text=self.t("btn_start"), height=40, width=210, fg_color=theme.ACCENT_CYAN, hover_color=theme.ACCENT_CYAN_HOVER, text_color="#101318", font=ctk.CTkFont(size=12, weight="bold"), corner_radius=5, command=self._on_action_btn_clicked)
        self.action_btn.pack(side="left", padx=(0, 8))
        self.copy_btn = ctk.CTkButton(actions, text=self.t("copy_mcp_url"), height=40, fg_color=theme.BG_SURFACE_ALT, hover_color=theme.BG_INPUT, text_color=theme.TEXT_PRIMARY, border_width=1, border_color=theme.BORDER_SUBTLE, font=ctk.CTkFont(size=11, weight="bold"), corner_radius=5, command=self._copy_public_url)
        self.copy_btn.pack(side="left", padx=4)
        self.open_chatgpt_btn = ctk.CTkButton(actions, text=self.t("open_chatgpt_btn"), height=40, fg_color=theme.BG_SURFACE_ALT, hover_color=theme.BG_INPUT, text_color=theme.TEXT_PRIMARY, border_width=1, border_color=theme.BORDER_SUBTLE, font=ctk.CTkFont(size=11, weight="bold"), corner_radius=5, command=lambda: webbrowser.open("https://chatgpt.com/#settings/Connectors"))
        self.open_chatgpt_btn.pack(side="left", padx=4)
        self.open_admin_ui_btn = ctk.CTkButton(actions, text=self.t("open_admin_ui_btn"), height=40, fg_color=theme.BG_SURFACE_ALT, hover_color=theme.BG_INPUT, text_color=theme.TEXT_PRIMARY, border_width=1, border_color=theme.BORDER_SUBTLE, font=ctk.CTkFont(size=11, weight="bold"), corner_radius=5, command=self._open_admin_ui)
        self.open_admin_ui_btn.pack(side="left", padx=4)
        self.doctor_btn = ctk.CTkButton(actions, text=self.t("btn_doctor"), height=40, fg_color="transparent", hover_color=theme.BG_SURFACE_ALT, text_color=theme.TEXT_SECONDARY, border_width=1, border_color=theme.BORDER_SUBTLE, font=ctk.CTkFont(size=10), corner_radius=5, command=self._run_diagnostics)
        self.doctor_btn.pack(side="right")

        health = ctk.CTkFrame(page, fg_color=theme.BG_SURFACE, corner_radius=6, border_width=1, border_color=theme.BORDER_SUBTLE)
        health.pack(fill="x", pady=10)
        ctk.CTkLabel(health, text="LOCAL SERVICES", anchor="w", font=ctk.CTkFont(size=9, weight="bold"), text_color=theme.TEXT_MUTED).pack(fill="x", padx=18, pady=(14, 8))
        self._health_row(health, "CodeLocal Backend", "Port 3333", "backend")
        self._health_row(health, "MCP transport", "Local service", "mcp")
        self._health_row(health, "Tunnel client", "Runtime process", "tunnel")

        recent = ctk.CTkFrame(page, fg_color=theme.BG_SURFACE, corner_radius=6, border_width=1, border_color=theme.BORDER_SUBTLE)
        recent.pack(fill="x", pady=10)
        ctk.CTkLabel(recent, text="RECENT ACTIVITY", anchor="w", font=ctk.CTkFont(size=9, weight="bold"), text_color=theme.TEXT_MUTED).pack(fill="x", padx=18, pady=(14, 8))
        self.overview_activity = ctk.CTkLabel(recent, text="No recent activity.", anchor="w", justify="left", font=ctk.CTkFont(family="Consolas", size=10), text_color=theme.TEXT_SECONDARY)
        self.overview_activity.pack(fill="x", padx=18, pady=(0, 14))

    def _health_row(self, parent, label, detail, key):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", padx=18, pady=5)
        ctk.CTkLabel(row, text=label, anchor="w", font=ctk.CTkFont(size=11, weight="bold"), text_color=theme.TEXT_PRIMARY).pack(side="left")
        ctk.CTkLabel(row, text=detail, anchor="e", font=ctk.CTkFont(size=10), text_color=theme.TEXT_MUTED).pack(side="right")
        self.health_labels[key] = ctk.CTkLabel(row, text="●", width=18, font=ctk.CTkFont(size=10), text_color=theme.COLOR_OFFLINE)
        self.health_labels[key].pack(side="right", padx=(8, 0))

    def _build_cloudflare_page(self):
        page = self._new_page("cloudflare", "Cloudflare", "Configure a named or quick tunnel to your local MCP service")
        self._build_cloudflare_card(page)
        self.cf_card.pack(fill="x", pady=0)
        self.cf_start_btn = ctk.CTkButton(page, text=self.t("btn_start"), height=40, width=180, fg_color=theme.ACCENT_CYAN, hover_color=theme.ACCENT_CYAN_HOVER, text_color="#101318", font=ctk.CTkFont(size=12, weight="bold"), corner_radius=5, command=self._on_action_btn_clicked)
        self.cf_start_btn.pack(anchor="w", pady=(14, 0))

    def _build_openai_page(self):
        page = self._new_page("openai", "OpenAI Secure", "Connect a local MCP server through the OpenAI tunnel control plane")
        self._build_openai_card(page)
        self.oa_card.pack(fill="x", pady=0)
        self.oa_start_btn = ctk.CTkButton(page, text=self.t("btn_start"), height=40, width=180, fg_color=theme.ACCENT_CYAN, hover_color=theme.ACCENT_CYAN_HOVER, text_color="#101318", font=ctk.CTkFont(size=12, weight="bold"), corner_radius=5, command=self._on_action_btn_clicked)
        self.oa_start_btn.pack(anchor="w", pady=(14, 0))

    def _build_diagnostics_page(self):
        page = self._new_page("diagnostics", "Diagnostics", "Check binaries, local services and tunnel connectivity")
        box = ctk.CTkFrame(page, fg_color=theme.BG_SURFACE, corner_radius=6, border_width=1, border_color=theme.BORDER_SUBTLE)
        box.pack(fill="x")
        ctk.CTkLabel(box, text="SYSTEM CHECK", anchor="w", font=ctk.CTkFont(size=9, weight="bold"), text_color=theme.TEXT_MUTED).pack(fill="x", padx=18, pady=(16, 8))
        self.diagnostics_summary = ctk.CTkLabel(box, text="Run diagnostics to inspect the current environment.", anchor="w", justify="left", font=ctk.CTkFont(size=11), text_color=theme.TEXT_SECONDARY)
        self.diagnostics_summary.pack(fill="x", padx=18, pady=(0, 14))
        ctk.CTkButton(box, text="Run diagnostics", height=38, fg_color=theme.ACCENT_CYAN, hover_color=theme.ACCENT_CYAN_HOVER, text_color="#101318", font=ctk.CTkFont(size=11, weight="bold"), corner_radius=5, command=self._run_diagnostics).pack(anchor="w", padx=18, pady=(0, 16))

    def _build_activity_page(self):
        page = self._new_page("activity", "Activity Log", "Tunnel events and diagnostics output")
        self._build_terminal_console(parent=page)

    def _build_settings_page(self):
        page = self._new_page("settings", "Settings", "Application preferences")
        box = ctk.CTkFrame(page, fg_color=theme.BG_SURFACE, corner_radius=6, border_width=1, border_color=theme.BORDER_SUBTLE)
        box.pack(fill="x")
        ctk.CTkLabel(box, text="INTERFACE", anchor="w", font=ctk.CTkFont(size=9, weight="bold"), text_color=theme.TEXT_MUTED).pack(fill="x", padx=18, pady=(16, 12))
        row = ctk.CTkFrame(box, fg_color="transparent")
        row.pack(fill="x", padx=18, pady=(0, 14))
        ctk.CTkLabel(row, text="Language", anchor="w", font=ctk.CTkFont(size=11, weight="bold"), text_color=theme.TEXT_PRIMARY).pack(side="left")
        self.settings_lang = ctk.CTkOptionMenu(row, values=["Tiếng Việt", "English"], command=self._on_language_changed, width=130, height=32, fg_color=theme.BG_SURFACE_ALT, button_color=theme.BG_SURFACE_ALT, button_hover_color=theme.BG_INPUT, corner_radius=5)
        self.settings_lang.set("Tiếng Việt" if self.current_lang == "vi" else "English")
        self.settings_lang.pack(side="right")
        ctk.CTkLabel(box, text="Changes are saved automatically. Credentials continue to use the existing secure configuration store.", anchor="w", wraplength=650, justify="left", font=ctk.CTkFont(size=10), text_color=theme.TEXT_MUTED).pack(fill="x", padx=18, pady=(0, 16))


    # -------------------------------------------------------------------------
    # 1. Header Bar
    # -------------------------------------------------------------------------
    def _build_header(self, parent=None):
        parent = parent or self
        header = CardFrame(parent, height=72, fg_color=theme.BG_SURFACE)
        header.grid(row=0, column=0, sticky="ew", padx=24, pady=(18, 12))
        header.grid_columnconfigure(0, weight=1)

        header_content = ctk.CTkFrame(header, fg_color="transparent")
        header_content.pack(fill="x", padx=18, pady=10)

        # Left: App Icon & Title
        title_box = ctk.CTkFrame(header_content, fg_color="transparent")
        title_box.pack(side="left")

        self.title_label = ctk.CTkLabel(
            title_box,
            text=self.t("app_title"),
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=theme.ACCENT_CYAN,
        )
        self.title_label.pack(anchor="w")

        self.subtitle_label = ctk.CTkLabel(
            title_box,
            text=self.t("app_subtitle"),
            font=ctk.CTkFont(size=12),
            text_color=theme.TEXT_SECONDARY,
        )
        self.subtitle_label.pack(anchor="w")

        # Right: CodeLocal Backend Health & Language Switcher
        actions_box = ctk.CTkFrame(header_content, fg_color="transparent")
        actions_box.pack(side="right")

        # CodeLocal Backend Status Pill
        self.backend_status_badge = ctk.CTkLabel(
            actions_box,
            text=self.t("backend_offline"),
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=theme.COLOR_CONNECTING,
            fg_color="#182338",
            corner_radius=12,
            padx=10,
            pady=4,
        )
        self.backend_status_badge.pack(side="left", padx=(0, 8))

        self.start_backend_btn = ctk.CTkButton(
            actions_box,
            text=self.t("start_backend_btn"),
            width=100,
            height=28,
            fg_color=theme.ACCENT_CYAN,
            hover_color=theme.ACCENT_CYAN_HOVER,
            text_color="#000000",
            font=ctk.CTkFont(size=11, weight="bold"),
            corner_radius=6,
            command=self._on_start_backend_clicked,
        )
        self.start_backend_btn.pack(side="left", padx=(0, 14))

        # Language dropdown
        self.lang_option = ctk.CTkOptionMenu(
            actions_box,
            values=["Tiếng Việt", "English"],
            command=self._on_language_changed,
            width=105,
            height=28,
            fg_color=theme.BG_SURFACE_ALT,
            button_color="#1f2d48",
            button_hover_color=theme.ACCENT_BLUE,
            font=ctk.CTkFont(size=11),
        )
        self.lang_option.set("Tiếng Việt" if self.current_lang == "vi" else "English")
        self.lang_option.pack(side="left")

    # -------------------------------------------------------------------------
    # 2. Mode Selector (Segmented Pill Buttons)
    # -------------------------------------------------------------------------
    def _build_mode_selector(self, parent):
        self.mode_frame = ctk.CTkFrame(parent, fg_color="transparent")
        self.mode_frame.pack(fill="x", pady=(5, 10))

        selector_container = ctk.CTkFrame(
            self.mode_frame,
            fg_color=theme.BG_SURFACE_ALT,
            border_color=theme.BORDER_SUBTLE,
            border_width=1,
            corner_radius=10,
            height=44,
        )
        selector_container.pack(fill="x")
        selector_container.grid_columnconfigure((0, 1), weight=1)

        self.btn_mode_cf = ctk.CTkButton(
            selector_container,
            text=self.t("mode_cf"),
            height=36,
            corner_radius=8,
            font=ctk.CTkFont(size=13, weight="bold"),
            command=lambda: self._switch_mode("cloudflare"),
        )
        self.btn_mode_cf.grid(row=0, column=0, padx=4, pady=4, sticky="ew")

        self.btn_mode_oa = ctk.CTkButton(
            selector_container,
            text=self.t("mode_openai"),
            height=36,
            corner_radius=8,
            font=ctk.CTkFont(size=13, weight="bold"),
            command=lambda: self._switch_mode("openai"),
        )
        self.btn_mode_oa.grid(row=0, column=1, padx=4, pady=4, sticky="ew")

    # -------------------------------------------------------------------------
    # 2.2 Cloudflare Setup Card
    # -------------------------------------------------------------------------
    def _build_cloudflare_card(self, parent):
        self.cf_card = CardFrame(parent, fg_color=theme.BG_SURFACE)
        self.cf_card.pack(fill="x", pady=6)

        header = ctk.CTkFrame(self.cf_card, fg_color="transparent")
        header.pack(fill="x", padx=18, pady=(14, 8))

        self.cf_title_label = ctk.CTkLabel(
            header,
            text="☁️ " + self.t("cf_title"),
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color=theme.TEXT_PRIMARY,
        )
        self.cf_title_label.pack(side="left")

        # Form content
        form = ctk.CTkFrame(self.cf_card, fg_color="transparent")
        form.pack(fill="x", padx=18, pady=(0, 16))
        form.grid_columnconfigure(1, weight=1)

        # Row 1: Token
        self.cf_token_lbl = ctk.CTkLabel(
            form,
            text=self.t("cf_token_label"),
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=theme.TEXT_SECONDARY,
        )
        self.cf_token_lbl.grid(row=0, column=0, sticky="w", pady=(8, 2))

        self.cf_token_entry = PasswordEntryWithToggle(
            form,
            placeholder_text=self.t("cf_token_placeholder"),
            on_change=lambda val: self._on_field_changed(),
        )
        self.cf_token_entry.grid(row=0, column=1, sticky="ew", pady=(8, 2))

        self.cf_token_hint = ctk.CTkLabel(
            form,
            text=self.t("cf_token_hint"),
            font=ctk.CTkFont(size=11),
            text_color=theme.TEXT_MUTED,
        )
        self.cf_token_hint.grid(row=1, column=1, sticky="w", pady=(0, 8))

        # Row 2: Hostname
        self.cf_host_lbl = ctk.CTkLabel(
            form,
            text=self.t("cf_host_label"),
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=theme.TEXT_SECONDARY,
        )
        self.cf_host_lbl.grid(row=2, column=0, sticky="w", pady=(4, 2))

        self.cf_host_entry = ctk.CTkEntry(
            form,
            placeholder_text=self.t("cf_host_placeholder"),
            height=38,
            fg_color=theme.BG_INPUT,
            border_color=theme.BORDER_SUBTLE,
            text_color=theme.TEXT_PRIMARY,
            corner_radius=8,
        )
        self.cf_host_entry.grid(row=2, column=1, sticky="ew", pady=(4, 2))
        self.cf_host_entry.bind("<KeyRelease>", lambda e: self._on_cf_host_key())

        self.cf_host_hint = ctk.CTkLabel(
            form,
            text=self.t("cf_host_hint"),
            font=ctk.CTkFont(size=11),
            text_color=theme.TEXT_MUTED,
        )
        self.cf_host_hint.grid(row=3, column=1, sticky="w", pady=(0, 8))

        # Row 3: Target Service Port Selection
        self.cf_port_lbl = ctk.CTkLabel(
            form,
            text=self.t("cf_port_label"),
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=theme.TEXT_SECONDARY,
        )
        self.cf_port_lbl.grid(row=4, column=0, sticky="w", pady=(4, 2))

        port_box = ctk.CTkFrame(form, fg_color="transparent")
        port_box.grid(row=4, column=1, sticky="ew", pady=(4, 2))

        self.cf_service_option = ctk.CTkOptionMenu(
            port_box,
            values=[
                self.t("cf_port_backend"),
                self.t("cf_port_web"),
                self.t("cf_port_custom"),
            ],
            command=self._on_cf_service_changed,
            height=34,
            width=280,
            fg_color=theme.BG_SURFACE_ALT,
            button_color="#1f2d48",
        )
        self.cf_service_option.pack(side="left", padx=(0, 10))

        self.cf_custom_port_entry = ctk.CTkEntry(
            port_box,
            width=80,
            height=34,
            placeholder_text="3333",
            fg_color=theme.BG_INPUT,
            border_color=theme.BORDER_SUBTLE,
        )
        # Hidden by default unless custom is selected

        # Row 4: Quick Tunnel Option
        self.cf_quick_check = ctk.CTkCheckBox(
            form,
            text=self.t("cf_quick_tunnel"),
            font=ctk.CTkFont(size=12),
            text_color=theme.TEXT_SECONDARY,
            fg_color=theme.ACCENT_CYAN,
            hover_color=theme.ACCENT_CYAN_HOVER,
            command=self._on_field_changed,
        )
        self.cf_quick_check.grid(row=5, column=1, sticky="w", pady=(8, 2))

    # -------------------------------------------------------------------------
    # 2.3 OpenAI Setup Card
    # -------------------------------------------------------------------------
    def _build_openai_card(self, parent):
        self.oa_card = CardFrame(parent, fg_color=theme.BG_SURFACE)
        self.oa_card.pack(fill="x", pady=6)

        header = ctk.CTkFrame(self.oa_card, fg_color="transparent")
        header.pack(fill="x", padx=18, pady=(14, 8))

        self.oa_title_label = ctk.CTkLabel(
            header,
            text="🤖 " + self.t("oa_title"),
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color=theme.TEXT_PRIMARY,
        )
        self.oa_title_label.pack(side="left")

        # Form content
        form = ctk.CTkFrame(self.oa_card, fg_color="transparent")
        form.pack(fill="x", padx=18, pady=(0, 16))
        form.grid_columnconfigure(1, weight=1)

        # Row 1: Tunnel ID
        self.oa_id_lbl = ctk.CTkLabel(
            form,
            text=self.t("oa_id_label"),
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=theme.TEXT_SECONDARY,
        )
        self.oa_id_lbl.grid(row=0, column=0, sticky="w", pady=(8, 2))

        oa_id_box = ctk.CTkFrame(form, fg_color="transparent")
        oa_id_box.grid(row=0, column=1, sticky="ew", pady=(8, 2))

        self.oa_id_entry = ctk.CTkEntry(
            oa_id_box,
            placeholder_text=self.t("oa_id_placeholder"),
            height=38,
            fg_color=theme.BG_INPUT,
            border_color=theme.BORDER_SUBTLE,
            text_color=theme.TEXT_PRIMARY,
            corner_radius=8,
        )
        self.oa_id_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.oa_id_entry.bind("<KeyRelease>", lambda e: self._on_oa_id_key())

        self.oa_id_validation_lbl = ctk.CTkLabel(
            oa_id_box,
            text="○",
            width=28,
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=theme.COLOR_OFFLINE,
        )
        self.oa_id_validation_lbl.pack(side="right")

        self.oa_id_hint = ctk.CTkLabel(
            form,
            text=self.t("oa_id_hint"),
            font=ctk.CTkFont(size=11),
            text_color=theme.TEXT_MUTED,
        )
        self.oa_id_hint.grid(row=1, column=1, sticky="w", pady=(0, 8))

        # Row 2: Runtime API Key
        self.oa_key_lbl = ctk.CTkLabel(
            form,
            text=self.t("oa_key_label"),
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=theme.TEXT_SECONDARY,
        )
        self.oa_key_lbl.grid(row=2, column=0, sticky="w", pady=(4, 2))

        self.oa_key_entry = PasswordEntryWithToggle(
            form,
            placeholder_text=self.t("oa_key_placeholder"),
            on_change=lambda val: self._on_field_changed(),
        )
        self.oa_key_entry.grid(row=2, column=1, sticky="ew", pady=(4, 2))

        self.oa_key_hint = ctk.CTkLabel(
            form,
            text=self.t("oa_key_hint"),
            font=ctk.CTkFont(size=11),
            text_color=theme.TEXT_MUTED,
        )
        self.oa_key_hint.grid(row=3, column=1, sticky="w", pady=(0, 8))

        # Row 3: CodeLocal Bearer Token
        self.oa_bearer_lbl = ctk.CTkLabel(
            form,
            text=self.t("oa_bearer_label"),
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=theme.TEXT_SECONDARY,
        )
        self.oa_bearer_lbl.grid(row=4, column=0, sticky="w", pady=(4, 2))

        bearer_box = ctk.CTkFrame(form, fg_color="transparent")
        bearer_box.grid(row=4, column=1, sticky="ew", pady=(4, 2))
        bearer_box.grid_columnconfigure(0, weight=1)

        self.oa_bearer_entry = PasswordEntryWithToggle(
            bearer_box,
            placeholder_text=self.t("oa_bearer_placeholder"),
            on_change=lambda val: self._on_field_changed(),
        )
        self.oa_bearer_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))

        self.btn_gen_bearer = ctk.CTkButton(
            bearer_box,
            text=self.t("btn_gen_bearer"),
            command=self._generate_and_fill_bearer_token,
            height=36,
            width=130,
            fg_color="#1e293b",
            hover_color="#334155",
            text_color=theme.ACCENT_CYAN,
            font=ctk.CTkFont(size=12, weight="bold"),
        )
        self.btn_gen_bearer.pack(side="right")

        self.oa_bearer_hint = ctk.CTkLabel(
            form,
            text=self.t("oa_bearer_hint"),
            font=ctk.CTkFont(size=11),
            text_color=theme.TEXT_MUTED,
        )
        self.oa_bearer_hint.grid(row=5, column=1, sticky="w", pady=(0, 8))

        # Row 4: Local MCP URL
        self.oa_local_mcp_lbl = ctk.CTkLabel(
            form,
            text=self.t("oa_local_mcp_label"),
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=theme.TEXT_SECONDARY,
        )
        self.oa_local_mcp_lbl.grid(row=6, column=0, sticky="w", pady=(4, 2))

        self.oa_local_mcp_entry = ctk.CTkEntry(
            form,
            placeholder_text=self.t("oa_local_mcp_placeholder"),
            height=36,
            fg_color=theme.BG_INPUT,
            border_color=theme.BORDER_SUBTLE,
            text_color=theme.TEXT_PRIMARY,
            corner_radius=8,
        )
        self.oa_local_mcp_entry.grid(row=6, column=1, sticky="ew", pady=(4, 2))
        self.oa_local_mcp_entry.bind("<KeyRelease>", lambda e: self._on_field_changed())

    # -------------------------------------------------------------------------
    # 2.4 Active Connection & Action Control Center
    # -------------------------------------------------------------------------
    def _build_control_center(self, parent):
        self.ctrl_card = CardFrame(parent, fg_color=theme.BG_SURFACE_ALT, border_color="#263554")
        self.ctrl_card.pack(fill="x", pady=8)

        inner = ctk.CTkFrame(self.ctrl_card, fg_color="transparent")
        inner.pack(fill="x", padx=18, pady=16)
        inner.grid_columnconfigure(0, weight=1)

        # Row 1: Live Status Header + Badge + Uptime
        status_row = ctk.CTkFrame(inner, fg_color="transparent")
        status_row.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        status_row.grid_columnconfigure(0, weight=1)

        self.status_title_lbl = ctk.CTkLabel(
            status_row,
            text=self.t("status_title"),
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=theme.TEXT_PRIMARY,
        )
        self.status_title_lbl.pack(side="left")

        self.uptime_lbl = ctk.CTkLabel(
            status_row,
            text=self.t("uptime") + " --:--:--",
            font=ctk.CTkFont(family="Consolas", size=11),
            text_color=theme.TEXT_MUTED,
        )
        self.uptime_lbl.pack(side="right", padx=(10, 0))

        self.status_badge = StatusBadge(
            status_row,
            initial_text=self.t("status_offline"),
            initial_color=theme.COLOR_OFFLINE,
        )
        self.status_badge.pack(side="right")

        # Row 1.5: Status Detail Subtext Label
        self.status_detail_lbl = ctk.CTkLabel(
            inner,
            text=self.t("status_detail_offline"),
            font=ctk.CTkFont(size=12),
            text_color=theme.TEXT_SECONDARY,
            anchor="w",
            justify="left",
            wraplength=880,
        )
        self.status_detail_lbl.grid(row=1, column=0, sticky="ew", pady=(0, 10))

        # Row 2: Public MCP URL display
        self.public_url_field = CopyableField(
            inner,
            placeholder_text="https://... (Public MCP URL sẽ xuất hiện khi tunnel kết nối)",
            readonly=True,
        )
        self.public_url_field.grid(row=2, column=0, sticky="ew", pady=(0, 14))

        # Row 3: Action Buttons Bar
        btn_bar = ctk.CTkFrame(inner, fg_color="transparent")
        btn_bar.grid(row=3, column=0, sticky="ew")

        # Primary Start / Stop Button (prominent gradient style)
        self.action_btn = ctk.CTkButton(
            btn_bar,
            text=self.t("btn_start"),
            height=44,
            width=230,
            fg_color=theme.ACCENT_CYAN,
            hover_color=theme.ACCENT_CYAN_HOVER,
            text_color="#04131f",
            font=ctk.CTkFont(size=14, weight="bold"),
            corner_radius=8,
            command=self._on_action_btn_clicked,
        )
        self.action_btn.pack(side="left", padx=(0, 10))

        # Copy MCP URL button
        self.copy_btn = ctk.CTkButton(
            btn_bar,
            text=self.t("copy_mcp_url"),
            height=44,
            fg_color=theme.BG_SURFACE,
            hover_color=theme.ACCENT_BLUE,
            text_color=theme.TEXT_PRIMARY,
            border_color=theme.BORDER_SUBTLE,
            border_width=1,
            font=ctk.CTkFont(size=12, weight="bold"),
            corner_radius=8,
            command=self._copy_public_url,
        )
        self.copy_btn.pack(side="left", padx=(0, 10))

        # Open ChatGPT Connectors button
        self.open_chatgpt_btn = ctk.CTkButton(
            btn_bar,
            text=self.t("open_chatgpt_btn"),
            height=44,
            fg_color=theme.BG_SURFACE,
            hover_color="#10b981",
            text_color=theme.TEXT_PRIMARY,
            border_color=theme.BORDER_SUBTLE,
            border_width=1,
            font=ctk.CTkFont(size=12, weight="bold"),
            corner_radius=8,
            command=lambda: webbrowser.open("https://chatgpt.com/#settings/Connectors"),
        )
        self.open_chatgpt_btn.pack(side="left", padx=(0, 10))

        # Open Tunnel-Client Web UI button (visible in OpenAI mode)
        self.open_admin_ui_btn = ctk.CTkButton(
            btn_bar,
            text=self.t("open_admin_ui_btn"),
            height=44,
            fg_color=theme.BG_SURFACE,
            hover_color="#8b5cf6",
            text_color=theme.TEXT_PRIMARY,
            border_color=theme.BORDER_SUBTLE,
            border_width=1,
            font=ctk.CTkFont(size=12, weight="bold"),
            corner_radius=8,
            command=self._open_admin_ui,
        )
        # Packed conditionally in _switch_mode

        # Diagnostics / Doctor button
        self.doctor_btn = ctk.CTkButton(
            btn_bar,
            text=self.t("btn_doctor"),
            height=44,
            fg_color=theme.BG_SURFACE,
            hover_color=theme.ACCENT_CYAN_HOVER,
            text_color=theme.TEXT_SECONDARY,
            border_color=theme.BORDER_SUBTLE,
            border_width=1,
            font=ctk.CTkFont(size=11),
            corner_radius=8,
            command=self._run_diagnostics,
        )
        self.doctor_btn.pack(side="right")

    # -------------------------------------------------------------------------
    # 2.5 Quick Integration Guide Card
    # -------------------------------------------------------------------------
    def _build_guide_card(self, parent):
        self.guide_card = CardFrame(parent, fg_color="#0d1424", border_color="#1d283f")
        self.guide_card.pack(fill="x", pady=(4, 10))

        inner = ctk.CTkFrame(self.guide_card, fg_color="transparent")
        inner.pack(fill="x", padx=16, pady=12)

        self.guide_title_lbl = ctk.CTkLabel(
            inner,
            text=self.t("guide_title"),
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=theme.TEXT_CYAN,
        )
        self.guide_title_lbl.pack(anchor="w", pady=(0, 4))

        self.guide_text_lbl = ctk.CTkLabel(
            inner,
            text=self.t("guide_text"),
            font=ctk.CTkFont(size=11),
            text_color=theme.TEXT_SECONDARY,
            justify="left",
        )
        self.guide_text_lbl.pack(anchor="w")

    # -------------------------------------------------------------------------
    # 3. Log Terminal Console
    # -------------------------------------------------------------------------
    def _build_terminal_console(self, parent=None):
        parent = parent or self
        console_card = CardFrame(parent, fg_color=theme.BG_TERMINAL, border_color=theme.BORDER_SUBTLE)
        if parent is self:
            console_card.grid(row=2, column=0, sticky="nsew", padx=20, pady=(0, 10))
            console_card.grid_columnconfigure(0, weight=1)
            console_card.grid_rowconfigure(1, weight=1)
        else:
            console_card.pack(fill="both", expand=True, pady=(0, 8))
            console_card.pack_propagate(False)

        # Header of Console
        top_bar = ctk.CTkFrame(console_card, fg_color="transparent", height=32)
        top_bar.grid(row=0, column=0, sticky="ew", padx=14, pady=(8, 4))
        top_bar.grid_columnconfigure(0, weight=1)

        self.logs_title_lbl = ctk.CTkLabel(
            top_bar,
            text="💻 " + self.t("logs_title"),
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=theme.TEXT_SECONDARY,
        )
        self.logs_title_lbl.pack(side="left")

        self.auto_scroll_check = ctk.CTkCheckBox(
            top_bar,
            text=self.t("btn_auto_scroll"),
            font=ctk.CTkFont(size=11),
            text_color=theme.TEXT_MUTED,
            fg_color=theme.ACCENT_CYAN,
            hover_color=theme.ACCENT_CYAN_HOVER,
            command=self._on_auto_scroll_toggle,
            width=80,
            checkbox_width=16,
            checkbox_height=16,
        )
        self.auto_scroll_check.select()
        self.auto_scroll_check.pack(side="right", padx=(10, 0))

        self.clear_log_btn = ctk.CTkButton(
            top_bar,
            text=self.t("btn_clear_log"),
            width=70,
            height=24,
            fg_color=theme.BG_SURFACE_ALT,
            hover_color="#243450",
            text_color=theme.TEXT_SECONDARY,
            font=ctk.CTkFont(size=11),
            corner_radius=5,
            command=self._clear_logs,
        )
        self.clear_log_btn.pack(side="right", padx=(10, 0))

        self.open_log_btn = ctk.CTkButton(
            top_bar,
            text=self.t("btn_open_log"),
            width=84,
            height=24,
            fg_color=theme.BG_SURFACE_ALT,
            hover_color="#243450",
            text_color=theme.TEXT_SECONDARY,
            font=ctk.CTkFont(size=11),
            corner_radius=5,
            command=self._open_log_file,
        )
        self.open_log_btn.pack(side="right")

        # Monospaced Text Box
        self.log_text = tk.Text(
            console_card,
            bg=theme.BG_TERMINAL,
            fg="#cbd5e1",
            insertbackground=theme.ACCENT_CYAN,
            selectbackground=theme.ACCENT_BLUE,
            font=("Consolas", 10),
            borderwidth=0,
            highlightthickness=0,
            wrap="word",
        )
        self.log_text.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 10))

        # Tag Styling for Color-Coded Logs
        self.log_text.tag_config("SYSTEM", foreground="#94a3b8")
        self.log_text.tag_config("CLOUDFLARE", foreground="#38bdf8")
        self.log_text.tag_config("TUNNEL-CLIENT", foreground="#c084fc")
        self.log_text.tag_config("SUCCESS", foreground="#34d399")
        self.log_text.tag_config("WARN", foreground="#fbbf24")
        self.log_text.tag_config("ERROR", foreground="#f87171")
        self.log_text.tag_config("TIMESTAMP", foreground="#475569")

    # -------------------------------------------------------------------------
    # 4. Bottom Footer Status Bar
    # -------------------------------------------------------------------------
    def _build_footer(self, parent=None):
        parent = parent or self
        footer = ctk.CTkFrame(parent, fg_color="transparent", height=24)
        footer.grid(row=2, column=0, sticky="ew", padx=24, pady=(0, 6))

        bins = self.tunnel_mgr.check_binaries()
        cf_v = bins["cloudflared"]["version"]
        tc_v = bins["tunnel_client"]["version"]

        self.footer_bins_lbl = ctk.CTkLabel(
            footer,
            text=f"Binaries: cloudflared ({cf_v}) | tunnel-client ({tc_v})",
            font=ctk.CTkFont(size=10),
            text_color=theme.TEXT_MUTED,
        )
        self.footer_bins_lbl.pack(side="left")

        self.footer_tip_lbl = ctk.CTkLabel(
            footer,
            text="CodeLocal Universal MCP Connection Layer",
            font=ctk.CTkFont(size=10),
            text_color=theme.TEXT_MUTED,
        )
        self.footer_tip_lbl.pack(side="right")

    # -------------------------------------------------------------------------
    # UI Logic & Mode Switching
    # -------------------------------------------------------------------------
    def _switch_mode(self, mode: str, save: bool = True):
        """Backward-compatible mode API; navigation now owns the visible page."""
        mode = "cloudflare" if mode == "cloudflare" else "openai"
        self.selected_mode = mode
        if save:
            self.config_mgr.set("selected_mode", mode)
            self.config_mgr.save()
        if hasattr(self, "pages"):
            self._show_page(mode)

    def _open_admin_ui(self):
        url = self.tunnel_mgr.admin_ui_url
        if not url and os.path.isfile(self.tunnel_mgr.health_url_file):
            try:
                with open(self.tunnel_mgr.health_url_file, "r", encoding="utf-8") as f:
                    base = f.read().strip()
                    if base:
                        url = f"{base}/ui"
            except Exception:
                pass
        if url:
            webbrowser.open(url)
        else:
            messagebox.showinfo(
                self.t("info_title"),
                "Chưa có Tunnel Web UI. Web UI chỉ hoạt động khi OpenAI Tunnel đang chạy!"
                if self.current_lang == "vi"
                else "Tunnel Web UI is available only when OpenAI Secure Tunnel is active!",
            )

    def _on_cf_service_changed(self, choice: str):
        if choice == self.t("cf_port_custom"):
            self.cf_custom_port_entry.pack(side="left", padx=5)
        else:
            self.cf_custom_port_entry.pack_forget()
        self._on_field_changed()
        self._update_cf_preview_url()

    def _on_cf_host_key(self):
        self._on_field_changed()
        self._update_cf_preview_url()

    def _update_cf_preview_url(self):
        if self.tunnel_mgr.running:
            return
        host = self.cf_host_entry.get().strip().lower()
        if host.startswith("https://"):
            host = host[8:]
        elif host.startswith("http://"):
            host = host[7:]
        host = host.split("/")[0].strip()
        if host:
            self.public_url_field.set(f"https://{host}/mcp")
        else:
            self.public_url_field.set("")

    def _on_oa_id_key(self):
        val = self.oa_id_entry.get().strip().lower()
        if re.fullmatch(r"tunnel_[0-9a-f]{32}", val):
            self.oa_id_validation_lbl.configure(text="✓", text_color=theme.COLOR_ONLINE)
        elif val:
            self.oa_id_validation_lbl.configure(text="⚠", text_color=theme.COLOR_CONNECTING)
        else:
            self.oa_id_validation_lbl.configure(text="○", text_color=theme.COLOR_OFFLINE)
        self._on_field_changed()
        self._update_oa_preview_url()

    def _update_oa_preview_url(self):
        if self.tunnel_mgr.running:
            return
        tid = self.oa_id_entry.get().strip().lower()
        if tid:
            self.public_url_field.set(f"tunnel://{tid}")
        else:
            self.public_url_field.set("")

    def _generate_and_fill_bearer_token(self):
        token = CodeLocalDetector.generate_local_bearer_token()
        self.oa_bearer_entry.set(token)
        self.config_mgr.set_openai_bearer_token(token)
        self.config_mgr.save()
        self.tunnel_mgr.log("SUCCESS", "Đã tạo CodeLocal Bearer Token tự động cho tài khoản (Hiệu lực 365 ngày).")
        orig_text = self.t("btn_gen_bearer")
        self.btn_gen_bearer.configure(text=self.t("copied"), fg_color=theme.COLOR_ONLINE, text_color="#ffffff")
        self.after(2000, lambda: self.btn_gen_bearer.configure(text=orig_text, fg_color="#1e293b", text_color=theme.ACCENT_CYAN))

    def _on_field_changed(self):
        """Save form state into config manager."""
        # Cloudflare
        self.config_mgr.set_cloudflare_token(self.cf_token_entry.get().strip())
        self.config_mgr.set_cloudflare_hostname(self.cf_host_entry.get().strip())
        selected_svc = self.cf_service_option.get()
        if selected_svc == self.t("cf_port_web"):
            self.config_mgr.set("cloudflare.target_service", "web")
        elif selected_svc == self.t("cf_port_custom"):
            self.config_mgr.set("cloudflare.target_service", "custom")
            try:
                p = int(self.cf_custom_port_entry.get().strip())
                self.config_mgr.set("cloudflare.custom_port", p)
            except ValueError:
                pass
        else:
            self.config_mgr.set("cloudflare.target_service", "backend")

        self.config_mgr.set("cloudflare.quick_tunnel", bool(self.cf_quick_check.get()))

        # OpenAI
        self.config_mgr.set_openai_tunnel_id(self.oa_id_entry.get().strip().lower())
        self.config_mgr.set_openai_runtime_api_key(self.oa_key_entry.get().strip())
        self.config_mgr.set_openai_bearer_token(self.oa_bearer_entry.get().strip())
        self.config_mgr.set_openai_local_mcp_url(self.oa_local_mcp_entry.get().strip())

        self.config_mgr.save()

    def _load_saved_data(self):
        """Populate widgets with stored values."""
        # Cloudflare
        self.cf_token_entry.set(self.config_mgr.get_cloudflare_token())
        self.cf_host_entry.insert(0, self.config_mgr.get_cloudflare_hostname())
        svc = self.config_mgr.get("cloudflare.target_service", "backend")
        if svc == "web":
            self.cf_service_option.set(self.t("cf_port_web"))
        elif svc == "custom":
            self.cf_service_option.set(self.t("cf_port_custom"))
            self.cf_custom_port_entry.insert(0, str(self.config_mgr.get("cloudflare.custom_port", 3333)))
            self.cf_custom_port_entry.pack(side="left", padx=5)
        else:
            self.cf_service_option.set(self.t("cf_port_backend"))

        if self.config_mgr.get("cloudflare.quick_tunnel", False):
            self.cf_quick_check.select()
        else:
            self.cf_quick_check.deselect()

        # OpenAI
        oa_id = self.config_mgr.get_openai_tunnel_id()
        self.oa_id_entry.insert(0, oa_id)
        if re.fullmatch(r"tunnel_[0-9a-f]{32}", oa_id):
            self.oa_id_validation_lbl.configure(text="✓", text_color=theme.COLOR_ONLINE)

        self.oa_key_entry.set(self.config_mgr.get_openai_runtime_api_key())
        self.oa_bearer_entry.set(self.config_mgr.get_openai_bearer_token())
        self.oa_local_mcp_entry.insert(0, self.config_mgr.get_openai_local_mcp_url())

        # Load recent activity logs if file exists
        if os.path.isfile(self.tunnel_mgr.log_file_path):
            try:
                with open(self.tunnel_mgr.log_file_path, "r", encoding="utf-8") as f:
                    lines = f.readlines()[-60:]
                    for l in lines:
                        self._append_log_line("SYSTEM", l.strip())
            except Exception:
                pass

    # -------------------------------------------------------------------------
    # Actions & Start / Stop Trigger
    # -------------------------------------------------------------------------
    def _on_action_btn_clicked(self):
        if self.tunnel_mgr.running:
            self.action_btn.configure(text=self.t("btn_stopping"), state="disabled")
            threading.Thread(target=self._stop_tunnel_async, daemon=True).start()
        else:
            self._save_and_start_tunnel()

    def _save_and_start_tunnel(self):
        self._on_field_changed()

        if self.selected_mode == "cloudflare":
            token = self.config_mgr.get_cloudflare_token()
            hostname = self.config_mgr.get_cloudflare_hostname()
            target_port = self.config_mgr.get_cloudflare_target_port()
            quick_tunnel = self.config_mgr.get("cloudflare.quick_tunnel", False)

            if not quick_tunnel and not token:
                messagebox.showwarning(
                    self.t("warn_title"),
                    self.t("err_missing_token"),
                )
                return

            if not quick_tunnel and not hostname:
                messagebox.showwarning(
                    self.t("warn_title"),
                    self.t("err_missing_host"),
                )
                return

            self.action_btn.configure(text=self.t("btn_starting"), state="disabled")
            threading.Thread(
                target=lambda: self.tunnel_mgr.start_cloudflare_tunnel(
                    token=token,
                    hostname=hostname,
                    target_port=target_port,
                    quick_tunnel=quick_tunnel,
                ),
                daemon=True,
            ).start()

        else:
            # OpenAI Mode
            tunnel_id = self.config_mgr.get_openai_tunnel_id()
            api_key = self.config_mgr.get_openai_runtime_api_key()
            bearer_token = self.config_mgr.get_openai_bearer_token()
            alias = self.config_mgr.get_openai_alias()
            local_mcp_url = self.config_mgr.get_openai_local_mcp_url()

            if not re.fullmatch(r"tunnel_[0-9a-f]{32}", tunnel_id):
                messagebox.showwarning(
                    self.t("warn_title"),
                    self.t("err_invalid_tid"),
                )
                return

            if not api_key:
                messagebox.showwarning(
                    self.t("warn_title"),
                    self.t("err_missing_key"),
                )
                return

            self.action_btn.configure(text=self.t("btn_starting"), state="disabled")
            threading.Thread(
                target=lambda: self.tunnel_mgr.start_openai_tunnel(
                    tunnel_id=tunnel_id,
                    runtime_api_key=api_key,
                    bearer_token=bearer_token,
                    alias=alias,
                    local_mcp_url=local_mcp_url,
                ),
                daemon=True,
            ).start()

    def _stop_tunnel_async(self):
        self.tunnel_mgr.stop()

    def _copy_public_url(self):
        url = self.public_url_field.get().strip()
        if not url:
            messagebox.showinfo(
                "Thông báo" if self.current_lang == "vi" else "Info",
                "Chưa có Public MCP URL. Hãy khởi động tunnel trước!"
                if self.current_lang == "vi"
                else "No public URL available yet. Start the tunnel first!",
            )
            return
        self.clipboard_clear()
        self.clipboard_append(url)
        self.update()

        orig_text = self.copy_btn.cget("text")
        self.copy_btn.configure(text=self.t("copied"), fg_color=theme.COLOR_ONLINE)
        self.after(1600, lambda: self.copy_btn.configure(text=orig_text, fg_color=theme.BG_SURFACE))

    def _on_start_backend_clicked(self):
        self.start_backend_btn.configure(text="Đang mở..." if self.current_lang == "vi" else "Opening...", state="disabled")
        ok = self.detector.launch_backend()
        if ok:
            self._append_log_line("SYSTEM", "Sent launch request for CodeLocal Cloud Backend.")
        else:
            self._append_log_line("WARN", "Could not locate backend start scripts in codelocal folder.")
        self.after(4000, lambda: self.start_backend_btn.configure(text=self.t("start_backend_btn"), state="normal"))

    def _run_diagnostics(self):
        self._append_log_line("SYSTEM", "--- BẮT ĐẦU KIỂM TRA CHẨN ĐOÁN (DIAGNOSTICS) ---")
        bins = self.tunnel_mgr.check_binaries()
        for name, b in bins.items():
            status = "FOUND" if b["found"] else "MISSING"
            self._append_log_line("SYSTEM", f"Binary [{name}]: {status} ({b['version']}) -> {b['path']}")

        # Probe CodeLocal
        res = self.detector.check_all()
        bk_status = "ONLINE" if res["backend_running"] else "OFFLINE"
        wb_status = "ONLINE" if res["web_running"] else "OFFLINE"
        self._append_log_line("SYSTEM", f"CodeLocal Backend (Port 3333): {bk_status}")
        self._append_log_line("SYSTEM", f"CodeLocal Web UI (Port 3000):  {wb_status}")
        self._append_log_line("SYSTEM", f"MCP Target URL:                {res['mcp_url']}")

        # Deep tunnel doctor
        tid = self.config_mgr.get_openai_tunnel_id()
        key = self.config_mgr.get_openai_runtime_api_key()
        mcp_url = self.config_mgr.get_openai_local_mcp_url()
        doc_lines = self.tunnel_mgr.run_doctor(tunnel_id=tid, api_key=key, mcp_url=mcp_url)
        for line in doc_lines:
            self._append_log_line("SYSTEM", line)
        self._append_log_line("SYSTEM", "--- KẾT THÚC CHẨN ĐOÁN ---")

    # -------------------------------------------------------------------------
    # Callbacks & Queue Handlers
    # -------------------------------------------------------------------------
    def _on_tunnel_status(self, state: str, public_url: str, message: str):
        self._ui_queue.put(("STATUS", (state, public_url, message)))

    def _on_tunnel_log(self, level: str, text: str):
        self._ui_queue.put(("LOG", (level, text)))

    def _process_ui_queue(self):
        if self._closing:
            return
        try:
            while not self._ui_queue.empty():
                event_type, data = self._ui_queue.get_nowait()
                if event_type == "STATUS":
                    state, public_url, message = data
                    self._update_status_ui(state, public_url, message)
                elif event_type == "LOG":
                    level, text = data
                    self._append_log_line(level, text)
        except Exception:
            pass
        self.after(100, self._process_ui_queue)

    def _update_status_ui(self, state: str, public_url: str, message: str):
        if state == TunnelManager.STATE_ACTIVE:
            self.status_badge.set_status(self.t("status_active"), theme.COLOR_ONLINE)
            self.action_btn.configure(
                text=self.t("btn_stop"),
                fg_color=theme.COLOR_ERROR,
                hover_color="#be123c",
                state="normal",
            )
            detail = self.t("status_detail_active_cf") if self.selected_mode == "cloudflare" else self.t("status_detail_active_oa")
            if message and message != "Tunnel stopped":
                detail = f"{detail} ({message})"
            self.status_detail_lbl.configure(text=detail, text_color=theme.COLOR_ONLINE)
            if public_url:
                self.public_url_field.set(public_url)

        elif state == TunnelManager.STATE_STARTING:
            self.status_badge.set_status(self.t("status_starting"), theme.COLOR_CONNECTING)
            self.action_btn.configure(text=self.t("btn_starting"), state="disabled")
            self.status_detail_lbl.configure(
                text=message or self.t("status_detail_starting"),
                text_color=theme.COLOR_CONNECTING,
            )

        elif state == TunnelManager.STATE_RECONNECTING:
            self.status_badge.set_status(self.t("status_reconnecting"), theme.COLOR_CONNECTING)
            self.action_btn.configure(
                text=self.t("btn_stop"),
                fg_color=theme.COLOR_ERROR,
                hover_color="#be123c",
                state="normal",
            )
            self.status_detail_lbl.configure(
                text=f"⚠ {message}" if message else self.t("status_reconnecting"),
                text_color=theme.COLOR_CONNECTING,
            )

        elif state == TunnelManager.STATE_ERROR:
            self.status_badge.set_status(self.t("status_error"), theme.COLOR_ERROR)
            self.action_btn.configure(
                text=self.t("btn_start"),
                fg_color=theme.ACCENT_CYAN,
                hover_color=theme.ACCENT_CYAN_HOVER,
                state="normal",
            )
            self.status_detail_lbl.configure(
                text=f"❌ {message}" if message else self.t("status_error"),
                text_color=theme.COLOR_ERROR,
            )

        else:  # OFFLINE
            self.status_badge.set_status(self.t("status_offline"), theme.COLOR_OFFLINE)
            self.action_btn.configure(
                text=self.t("btn_start"),
                fg_color=theme.ACCENT_CYAN,
                hover_color=theme.ACCENT_CYAN_HOVER,
                state="normal",
            )
            self.status_detail_lbl.configure(
                text=message or self.t("status_detail_offline"),
                text_color=theme.TEXT_SECONDARY,
            )
            if self.selected_mode == "cloudflare":
                self._update_cf_preview_url()
            else:
                self._update_oa_preview_url()

    def _append_log_line(self, level: str, text: str):
        if self._closing:
            return
        ts = time.strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{ts}] ", "TIMESTAMP")
        self.log_text.insert(tk.END, f"[{level.upper()}] ", level.upper() if level.upper() in ("SYSTEM", "CLOUDFLARE", "TUNNEL-CLIENT", "SUCCESS", "WARN", "ERROR") else "SYSTEM")
        self.log_text.insert(tk.END, f"{text}\n")

        if self._auto_scroll:
            self.log_text.see(tk.END)

    def _clear_logs(self):
        self.log_text.delete("1.0", tk.END)

    def _open_log_file(self):
        p = self.tunnel_mgr.log_file_path
        if os.path.isfile(p):
            if sys.platform == "win32":
                os.startfile(p)
            else:
                subprocess.Popen(["xdg-open", p])
        else:
            messagebox.showinfo("Log File", "Chưa có file nhật ký." if self.current_lang == "vi" else "No log file exists yet.")

    def _on_auto_scroll_toggle(self):
        self._auto_scroll = bool(self.auto_scroll_check.get())

    # -------------------------------------------------------------------------
    # Periodic Loops
    # -------------------------------------------------------------------------
    def _check_codelocal_backend_loop(self):
        if self._closing:
            return

        def _check():
            res = self.detector.check_backend_status(port=3333, timeout=1.0)
            if not self._closing:
                self.after(0, lambda: self._update_backend_indicator(res["running"]))

        threading.Thread(target=_check, daemon=True).start()
        self.after(4000, self._check_codelocal_backend_loop)

    def _update_backend_indicator(self, is_online: bool):
        if is_online:
            self.backend_status_badge.configure(
                text=self.t("backend_online"),
                text_color=theme.COLOR_ONLINE,
                fg_color="#0e231d",
            )
            self.start_backend_btn.pack_forget()
        else:
            self.backend_status_badge.configure(
                text=self.t("backend_offline"),
                text_color=theme.COLOR_CONNECTING,
                fg_color="#241c10",
            )
            if not self.start_backend_btn.winfo_ismapped():
                self.start_backend_btn.pack(side="left", padx=(0, 14), after=self.backend_status_badge)

    def _update_uptime_loop(self):
        if self._closing:
            return
        if self.tunnel_mgr.running:
            self.uptime_lbl.configure(text=f"{self.t('uptime')} {self.tunnel_mgr.get_uptime_str()}")
        else:
            self.uptime_lbl.configure(text=f"{self.t('uptime')} --:--:--")
        self.after(1000, self._update_uptime_loop)

    # -------------------------------------------------------------------------
    # Language Switcher
    # -------------------------------------------------------------------------
    def _on_language_changed(self, choice: str):
        new_lang = "vi" if choice == "Tiếng Việt" else "en"
        if new_lang != self.current_lang:
            self.current_lang = new_lang
            self.config_mgr.set("language", new_lang)
            self.config_mgr.save()
            self._apply_translations()

    def _apply_translations(self):
        self.title_label.configure(text=self.t("app_title"))
        self.subtitle_label.configure(text=self.t("app_subtitle"))
        self.cf_title_label.configure(text="☁️ " + self.t("cf_title"))
        self.cf_token_lbl.configure(text=self.t("cf_token_label"))
        self.cf_token_hint.configure(text=self.t("cf_token_hint"))
        self.cf_host_lbl.configure(text=self.t("cf_host_label"))
        self.cf_host_hint.configure(text=self.t("cf_host_hint"))
        self.cf_port_lbl.configure(text=self.t("cf_port_label"))
        self.cf_quick_check.configure(text=self.t("cf_quick_tunnel"))
        self.oa_title_label.configure(text="🤖 " + self.t("oa_title"))
        self.oa_id_lbl.configure(text=self.t("oa_id_label"))
        self.oa_id_hint.configure(text=self.t("oa_id_hint"))
        self.oa_key_lbl.configure(text=self.t("oa_key_label"))
        self.oa_key_hint.configure(text=self.t("oa_key_hint"))
        self.oa_bearer_lbl.configure(text=self.t("oa_bearer_label"))
        self.oa_bearer_hint.configure(text=self.t("oa_bearer_hint"))
        self.btn_gen_bearer.configure(text=self.t("btn_gen_bearer"))
        self.oa_local_mcp_lbl.configure(text=self.t("oa_local_mcp_label"))
        self.status_title_lbl.configure(text=self.t("status_title"))
        self.copy_btn.configure(text=self.t("copy_mcp_url"))
        self.open_chatgpt_btn.configure(text=self.t("open_chatgpt_btn"))
        if hasattr(self, "open_admin_ui_btn"):
            self.open_admin_ui_btn.configure(text=self.t("open_admin_ui_btn"))
        self.doctor_btn.configure(text=self.t("btn_doctor"))
        self.guide_title_lbl.configure(text=self.t("guide_title"))
        self.guide_text_lbl.configure(text=self.t("guide_text"))
        self.logs_title_lbl.configure(text="💻 " + self.t("logs_title"))
        self.clear_log_btn.configure(text=self.t("btn_clear_log"))
        self.open_log_btn.configure(text=self.t("btn_open_log"))
        self.auto_scroll_check.configure(text=self.t("btn_auto_scroll"))
        self.start_backend_btn.configure(text=self.t("start_backend_btn"))

        # Synchronize service option menu localized values
        svc_values = [
            self.t("cf_port_backend"),
            self.t("cf_port_web"),
            self.t("cf_port_custom"),
        ]
        self.cf_service_option.configure(values=svc_values)
        curr_svc = self.config_mgr.get("cloudflare.target_service", "backend")
        if curr_svc == "web":
            self.cf_service_option.set(self.t("cf_port_web"))
        elif curr_svc == "custom":
            self.cf_service_option.set(self.t("cf_port_custom"))
        else:
            self.cf_service_option.set(self.t("cf_port_backend"))

        # Localize placeholders
        self.cf_token_entry.entry.configure(placeholder_text=self.t("cf_token_placeholder"))
        self.cf_host_entry.configure(placeholder_text=self.t("cf_host_placeholder"))
        self.oa_id_entry.configure(placeholder_text=self.t("oa_id_placeholder"))
        self.oa_key_entry.entry.configure(placeholder_text=self.t("oa_key_placeholder"))
        self.oa_local_mcp_entry.configure(placeholder_text=self.t("oa_local_mcp_placeholder"))

        # Re-trigger status update
        self._update_status_ui(self.tunnel_mgr.current_state, self.tunnel_mgr.public_url, self.tunnel_mgr.status_message)

    # -------------------------------------------------------------------------
    # Shutdown
    # -------------------------------------------------------------------------
    def on_closing(self):
        self._closing = True
        if self.tunnel_mgr.running:
            self.tunnel_mgr.stop()
        self.destroy()
