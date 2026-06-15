"""Timegrapher Studio core — pure-Python instrument engine.

This package must NOT import tkinter / customtkinter or any desktop-only
dependency. The desktop UI (ui/) and a future mobile UI (Flet) both sit on top
of exactly this code, so it stays framework-agnostic.
"""
