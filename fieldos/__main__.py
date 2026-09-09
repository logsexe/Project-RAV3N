from fieldos import app_v05

# OSINT remains a first-class operator category while retaining the legacy
# navigation constants used by inherited FIELD//OS views.
if not any(name == "OSINT" for name, _ in app_v05.CATEGORIES):
    app_v05.CATEGORIES.insert(2, ("OSINT", "Open-source intelligence / enrichment"))

from .app_v13 import FieldOSApp


def main() -> None:
    FieldOSApp().run()


if __name__ == "__main__":
    main()
