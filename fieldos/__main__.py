from fieldos import app_v05

# V1.2 promotes OSINT to a first-class operator category while retaining the
# legacy V0.5 navigation constants used by inherited views.
if not any(name == "OSINT" for name, _ in app_v05.CATEGORIES):
    app_v05.CATEGORIES.insert(2, ("OSINT", "Open-source intelligence / enrichment"))

from .app_v12 import FieldOSApp


def main() -> None:
    FieldOSApp().run()


if __name__ == "__main__":
    main()
