import os
import sys
from pathlib import Path

os.environ.setdefault("JWT_SECRET_KEY", "0123456789abcdef0123456789abcdef")
sys.path.insert(0, str(Path(__file__).parents[1]))
