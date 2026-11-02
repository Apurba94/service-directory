"""Start the app: python -m service_directory [data.db] [--port 8039]"""
import sys

from .fieldkit import main_cli
from .web import create_app

sys.exit(main_cli(create_app, "services.db", 8039, sys.argv))
