from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class Theme:
    id: str
    name: str
    background: str
    panel: str
    panel_focus: str
    text: str
    muted: str
    accent: str
    border: str


THEMES: tuple[Theme, ...] = (
    Theme("phosphor", "PHOSPHOR", "#030806", "#07100b", "#0a1710", "#bfffcf", "#65a875", "#7dff9b", "#2d6b3d"),
    Theme("amber", "AMBER CRT", "#090603", "#120d05", "#1a1206", "#ffd891", "#a77e42", "#ffb84d", "#6f4b18"),
    Theme("ice", "ICE BLUE", "#03070a", "#071017", "#0a1720", "#d4f1ff", "#6f9eaf", "#79d7ff", "#28546a"),
    Theme("red", "RED ALERT", "#090303", "#130606", "#1b0808", "#ffd2d2", "#a96b6b", "#ff6868", "#6b2525"),
    Theme("mono", "MONOCHROME", "#050607", "#0b0d0e", "#121516", "#e1e5e6", "#858c8f", "#ffffff", "#454b4e"),
)


class ThemeManager:
    def __init__(self) -> None:
        self.index = 0

    @property
    def current(self) -> Theme:
        return THEMES[self.index]

    def next(self) -> Theme:
        self.index = (self.index + 1) % len(THEMES)
        return self.current
