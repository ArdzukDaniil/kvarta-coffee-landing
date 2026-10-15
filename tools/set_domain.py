"""Подставить настоящий адрес сайта после деплоя.

    python tools/set_domain.py https://kvarta-xxx.vercel.app

Меняет адрес в canonical, Open Graph, schema.org, robots.txt, sitemap.xml и README.
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FILES = ["public/index.html", "public/robots.txt", "public/sitemap.xml", "README.md"]
CURRENT = re.compile(r"https://kvarta-coffee\.vercel\.app")


def main(new: str) -> None:
    new = new.rstrip("/")
    if not re.fullmatch(r"https://[a-z0-9.-]+", new):
        sys.exit("Нужен адрес вида https://имя.vercel.app")
    for name in FILES:
        path = ROOT / name
        text = path.read_text(encoding="utf-8")
        updated, count = CURRENT.subn(new, text)
        path.write_text(updated, encoding="utf-8")
        print(f"{name}: {count}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else sys.exit(__doc__))
