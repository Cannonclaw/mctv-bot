# Copyright (c) 2026 MCTV Digital, Inc. All rights reserved.
# Proprietary and confidential. Unauthorized copying, distribution,
# or modification of this file is strictly prohibited.

"""Fail a cron loudly when its configuration is missing.

Why this exists
---------------
``supabase_client._rest_request`` returns ``None`` when SUPABASE_URL or a key
is absent, and ``query_table`` turns that into ``[]``. Every cron script reads
an empty list as "nothing to do today" and returns 0, so Render paints the run
green and its "only failure notifications" setting never fires.

That is not hypothetical. In August 2026 a wave of cron jobs was created
pointing at an env group (``mctv-bot-env``) that did not exist. They ran daily
for weeks reporting success while doing nothing at all — ``mctv-stalled-alerts``
logged "Stalled deals: 0 across 0 reps" every weekday while 60 opportunities
sat past their thresholds untouched.

A missing credential is a configuration error, not an empty result set. Calling
``require_env`` at the top of a cron makes the two distinguishable from outside
the process: the job exits non-zero, Render marks it failed, and the existing
notification actually reaches someone.

Usage
-----
    from services.env_preflight import require_env

    def main() -> int:
        require_env("SUPABASE_URL", SUPABASE_ANY_KEY)
        ...
"""

import os
import sys

# Exit code 78 is sysexits.h EX_CONFIG ("configuration error"). Any non-zero
# code marks the Render run failed; 78 additionally distinguishes "misconfigured"
# from a script's own `return 1` business-logic abort in the logs.
EX_CONFIG = 78

# The service-role key is spelled two different ways across this codebase:
# services/supabase_client.py reads SUPABASE_SERVICE_KEY, while the newer
# drop-in modules (task_service, rate_service, field_notes_service,
# loop_inventory_service, scripts/daily_tasks.py) read
# SUPABASE_SERVICE_ROLE_KEY and fall back to SUPABASE_KEY. A cron is satisfied
# by any one of them, so require the group rather than a single name.
SUPABASE_ANY_KEY = (
    "SUPABASE_SERVICE_KEY",
    "SUPABASE_SERVICE_ROLE_KEY",
    "SUPABASE_KEY",
)


def _present(name: str) -> bool:
    """True when the variable is set to something other than whitespace.

    Render writes an empty string for a variable added with no value, which is
    indistinguishable from unset for our purposes and worse to debug.
    """
    return bool((os.environ.get(name) or "").strip())


def missing_env(*required) -> list:
    """Return the requirements that are not satisfied, without exiting.

    Each argument is either a variable name, or a tuple of alternative names
    of which at least one must be present (see ``SUPABASE_ANY_KEY``).
    Exposed separately from ``require_env`` so health checks and tests can ask
    the question without killing the process.
    """
    unmet = []
    for req in required:
        if isinstance(req, (tuple, list)):
            if not any(_present(name) for name in req):
                unmet.append(" or ".join(req))
        elif not _present(req):
            unmet.append(req)
    return unmet


def require_env(*required) -> None:
    """Exit EX_CONFIG unless every requirement is satisfied.

    Prints one line per missing requirement so the Render log names exactly
    what to set, rather than leaving the reader to infer it from a zero count.
    """
    unmet = missing_env(*required)
    if not unmet:
        return

    script = os.path.basename(sys.argv[0]) or "cron"
    print(
        f"[preflight] {script}: refusing to run — missing required "
        f"configuration ({len(unmet)}):",
        flush=True,
    )
    for name in unmet:
        print(f"[preflight]   - {name}", flush=True)
    print(
        "[preflight] Set these on the service, or attach the 'mctv-bot-env' "
        "environment group in the Render dashboard.",
        flush=True,
    )
    sys.exit(EX_CONFIG)
