import sys
import os
from unittest.mock import MagicMock

# weasyprint loads system libraries (libgobject, pango) at import time.
# Those aren't available outside Docker, so stub the module before any
# test file is collected — this lets us mock HTML/CSS in individual tests.
sys.modules["weasyprint"] = MagicMock()

# Make sure app/ is in the path so `import main` and `import converters` work
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
