from fieldos import app_v05

if not any(name == "OSINT" for name, _ in app_v05.CATEGORIES):
    app_v05.CATEGORIES.insert(2, ("OSINT", "Open-source intelligence / enrichment"))

from .app_v16 import FieldOSApp


def main() -> None:
    FieldOSApp().run()


if __name__ == "__main__":
    main()
