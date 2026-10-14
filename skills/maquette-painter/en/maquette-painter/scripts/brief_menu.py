"""Print the planning menu (every choice with its default) as Markdown.

Usage: python brief_menu.py [subject]     subject: portrait | figure | scene | landscape | still_life | stock
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from atelier import menu

if __name__ == "__main__":
    print(menu(sys.argv[1] if len(sys.argv) > 1 else None))
