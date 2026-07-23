# Copyright (c) 2026 MCTV Digital, Inc. All rights reserved.
# Proprietary and confidential. Unauthorized copying, distribution,
# or modification of this file is strictly prohibited.
"""Container entrypoint: register the public /rates route, then run Streamlit.

`streamlit run app.py` builds its HTTP routes before it ever executes
app.py, so the extra public route has to be registered from a wrapper that
imports server_routes first (see the module docstring there). Everything
else about how the app starts is identical to the plain
`streamlit run app.py` this replaced.
"""

import logging
import sys
from pathlib import Path

APP_SCRIPT = Path(__file__).parent / "app.py"


def main() -> int:
    import server_routes

    server_routes.install()

    sys.argv = [
        "streamlit",
        "run",
        str(APP_SCRIPT),
        "--server.port=8501",
        "--server.address=0.0.0.0",
        "--server.headless=true",
    ]
    from streamlit.web import cli as stcli

    return stcli.main()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    sys.exit(main())
