"""View registry — sidebar-driven view registration.

Direct analogue of SI-Docs' ModuleRegistry. Each view registers a key, display
name, 3-letter sidebar icon, its CTkFrame class, and a sort order. main_window
builds the sidebar from this and stacks the frames for instant tkraise switching.
"""
from __future__ import annotations


class ViewRegistry:
    _views: dict = {}

    @classmethod
    def register(cls, key, name, icon, ui_class, order=99):
        cls._views[key] = {
            "key": key, "name": name, "icon": icon,
            "ui_class": ui_class, "order": order,
        }

    @classmethod
    def get_views(cls):
        return sorted(cls._views.values(), key=lambda v: v["order"])
