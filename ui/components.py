import tkinter as tk
from typing import Callable, Optional
import customtkinter as ctk

from ui import theme


class CardFrame(ctk.CTkFrame):
    """Modern styled card container with rounded corners and clean borders."""

    def __init__(self, master, fg_color=theme.BG_SURFACE, border_color=theme.BORDER_SUBTLE, border_width=1, corner_radius=10, **kwargs):
        super().__init__(
            master,
            fg_color=fg_color,
            border_color=border_color,
            border_width=border_width,
            corner_radius=min(corner_radius, 7),
            **kwargs,
        )


class StatusBadge(ctk.CTkFrame):
    """Pill badge showing connection state with colored status dot."""

    def __init__(self, master, initial_text="● OFFLINE", initial_color=theme.COLOR_OFFLINE, **kwargs):
        super().__init__(master, fg_color="#0d1424", border_color=theme.BORDER_SUBTLE, border_width=1, corner_radius=20, height=32, **kwargs)
        self.pack_propagate(False)

        self.label = ctk.CTkLabel(
            self,
            text=initial_text,
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=initial_color,
        )
        self.label.pack(expand=True, padx=14, pady=4)

    def set_status(self, text: str, color: str):
        self.label.configure(text=text, text_color=color)


class PasswordEntryWithToggle(ctk.CTkFrame):
    """Text entry field with an integrated show/hide password toggle button."""

    def __init__(self, master, placeholder_text="", width=380, height=38, on_change: Optional[Callable[[str], None]] = None, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.on_change = on_change
        self.is_showing = False

        self.entry = ctk.CTkEntry(
            self,
            placeholder_text=placeholder_text,
            width=width - 50,
            height=height,
            show="•",
            fg_color=theme.BG_INPUT,
            border_color=theme.BORDER_SUBTLE,
            text_color=theme.TEXT_PRIMARY,
            placeholder_text_color=theme.TEXT_MUTED,
            corner_radius=8,
        )
        self.entry.pack(side="left", fill="x", expand=True, padx=(0, 6))

        if on_change:
            self.entry.bind("<KeyRelease>", lambda e: on_change(self.get()))

        self.toggle_btn = ctk.CTkButton(
            self,
            text="Show",
            width=42,
            height=height,
            fg_color=theme.BG_SURFACE_ALT,
            hover_color="#1f2d48",
            text_color=theme.TEXT_SECONDARY,
            corner_radius=8,
            command=self._toggle_visibility,
        )
        self.toggle_btn.pack(side="right")

    def _toggle_visibility(self):
        self.is_showing = not self.is_showing
        if self.is_showing:
            self.entry.configure(show="")
            self.toggle_btn.configure(text="🔒", text_color=theme.ACCENT_CYAN)
        else:
            self.entry.configure(show="•")
            self.toggle_btn.configure(text="👁", text_color=theme.TEXT_SECONDARY)

    def get(self) -> str:
        return self.entry.get()

    def set(self, value: str):
        self.entry.delete(0, tk.END)
        self.entry.insert(0, value)


class CopyableField(ctk.CTkFrame):
    """Read-only or editable text field with a 1-click copy button and feedback animation."""

    def __init__(self, master, placeholder_text="", default_value="", readonly=True, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.readonly = readonly

        self.entry = ctk.CTkEntry(
            self,
            placeholder_text=placeholder_text,
            height=38,
            fg_color=theme.BG_INPUT,
            border_color=theme.BORDER_SUBTLE,
            text_color=theme.ACCENT_CYAN,
            font=ctk.CTkFont(family="Consolas", size=12, weight="bold"),
            corner_radius=8,
        )
        self.entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        if default_value:
            self.set(default_value)

        self.copy_btn = ctk.CTkButton(
            self,
            text="📋 Copy",
            width=76,
            height=38,
            fg_color=theme.BG_SURFACE_ALT,
            hover_color=theme.ACCENT_BLUE,
            text_color=theme.TEXT_PRIMARY,
            corner_radius=8,
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self.copy_to_clipboard,
        )
        self.copy_btn.pack(side="right")

    def copy_to_clipboard(self):
        val = self.get().strip()
        if not val:
            return
        self.clipboard_clear()
        self.clipboard_append(val)
        self.update()

        orig_text = self.copy_btn.cget("text")
        orig_fg = self.copy_btn.cget("fg_color")
        self.copy_btn.configure(text="✓ Copied", fg_color=theme.COLOR_ONLINE)
        self.after(1600, lambda: self.copy_btn.configure(text=orig_text, fg_color=orig_fg))

    def get(self) -> str:
        return self.entry.get()

    def set(self, value: str):
        if self.readonly:
            self.entry.configure(state="normal")
        self.entry.delete(0, tk.END)
        self.entry.insert(0, value)
        if self.readonly:
            self.entry.configure(state="readonly")
