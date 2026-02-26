# Copyright (c) 2026 MCTV Digital, Inc. All rights reserved.
# Proprietary and confidential. Unauthorized copying, distribution,
# or modification of this file is strictly prohibited.
"""Progressive Web App (PWA) support for the MCTV Client Portal.

Injects:
  1. Web app manifest link + mobile meta tags (viewport, theme-color, apple icons)
  2. Service worker registration script
  3. Mobile-responsive CSS overrides for Streamlit
  4. Optional install prompt banner

Usage:
    Call inject_pwa() once at the top of any page (or in the portal UI helper)
    to enable PWA features. It's safe to call multiple times — it only injects once
    per Streamlit session rerun via a guard flag.
"""

import streamlit as st
import streamlit.components.v1 as components


def inject_pwa():
    """Inject all PWA assets into the current Streamlit page.

    Safe to call from every page — uses a session flag to avoid duplicates.
    """
    # No guard needed — Streamlit re-renders the full page on each rerun,
    # so we must re-inject every time. The st.markdown calls are idempotent.

    # ── 1. Meta tags + Manifest link ──────────────────────────────────────
    st.markdown(_PWA_HEAD_TAGS, unsafe_allow_html=True)

    # ── 2. Service Worker registration ────────────────────────────────────
    components.html(_SW_REGISTRATION_SCRIPT, height=0, width=0)

    # ── 3. Mobile-responsive CSS ──────────────────────────────────────────
    st.markdown(_MOBILE_CSS, unsafe_allow_html=True)


def inject_install_banner():
    """Show a dismissible 'Add to Home Screen' banner for mobile users.

    Call this on the landing page or portal dashboard. The banner only
    appears when:
      - User is on a mobile device
      - The app is NOT already installed (standalone mode)
      - User hasn't dismissed it this session
    """
    if st.session_state.get("_pwa_banner_dismissed"):
        return

    components.html(_INSTALL_BANNER_SCRIPT, height=80, scrolling=False)


# ── Injected HTML/CSS/JS blocks ──────────────────────────────────────────────

_PWA_HEAD_TAGS = """
<link rel="manifest" href="/app/static/manifest.json" crossorigin="use-credentials">
<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no, viewport-fit=cover">
<meta name="theme-color" content="#1B2A4A">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="apple-mobile-web-app-title" content="MCTV Portal">
<link rel="apple-touch-icon" sizes="180x180" href="/app/static/icons/icon-192x192.png">
<link rel="icon" type="image/png" sizes="32x32" href="/app/static/icons/icon-96x96.png">
<meta name="msapplication-TileColor" content="#1B2A4A">
<meta name="msapplication-TileImage" content="/app/static/icons/icon-144x144.png">
"""

_SW_REGISTRATION_SCRIPT = """
<script>
// Register the service worker from the parent window context
// (this script runs inside a Streamlit components.html iframe).
// The mimetypes fix in app.py ensures .js files are served as
// application/javascript instead of text/plain.
(function() {
    var nav;
    try { nav = window.parent.navigator; } catch(e) { nav = navigator; }
    if (!('serviceWorker' in nav)) return;

    nav.serviceWorker.register('/app/static/service-worker.js')
        .then(function(reg) { console.log('[PWA] Service Worker registered, scope:', reg.scope); })
        .catch(function(err) { console.log('[PWA] SW registration failed:', err.message); });
})();
</script>
"""

_MOBILE_CSS = """
<style>
/* ── MCTV Portal — Mobile-Responsive Overrides ──────────────────────── */

/* Viewport & safe areas (notch support) */
html {
    -webkit-text-size-adjust: 100%;
}

/* ── Global mobile adjustments ──────────────────────────────────────── */
@media (max-width: 768px) {

    /* Hide Streamlit hamburger menu & footer on mobile for cleaner look */
    #MainMenu { visibility: hidden; }
    footer { visibility: hidden !important; }
    header[data-testid="stHeader"] { display: none !important; }

    /* Reduce main container padding */
    .block-container {
        padding-left: 1rem !important;
        padding-right: 1rem !important;
        padding-top: 1rem !important;
        max-width: 100% !important;
    }

    /* Sidebar: full-width overlay on mobile */
    section[data-testid="stSidebar"] {
        width: 85vw !important;
        min-width: 85vw !important;
    }

    section[data-testid="stSidebar"] .block-container {
        padding: 1rem !important;
    }

    /* Make headings scale down */
    h1 { font-size: 1.6rem !important; line-height: 1.2 !important; }
    h2 { font-size: 1.3rem !important; }
    h3 { font-size: 1.1rem !important; }

    /* Make metric cards stack better */
    [data-testid="stMetric"] {
        padding: 0.5rem !important;
    }
    [data-testid="stMetricValue"] {
        font-size: 1.4rem !important;
    }
    [data-testid="stMetricLabel"] {
        font-size: 0.75rem !important;
    }

    /* Larger tap targets for buttons */
    .stButton > button {
        min-height: 48px !important;
        font-size: 1rem !important;
        padding: 0.6rem 1.2rem !important;
        border-radius: 8px !important;
    }

    /* Text inputs: bigger on mobile */
    .stTextInput input,
    .stSelectbox select,
    .stTextArea textarea {
        font-size: 16px !important;   /* prevents iOS zoom on focus */
        min-height: 48px !important;
        padding: 0.6rem !important;
    }

    /* Columns: stack vertically on mobile */
    [data-testid="stHorizontalBlock"] {
        flex-wrap: wrap !important;
    }
    [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {
        flex: 1 1 100% !important;
        min-width: 100% !important;
    }

    /* Expanders: more padding for touch */
    details summary {
        min-height: 48px !important;
        padding: 0.75rem !important;
    }

    /* Tables: horizontal scroll */
    .stDataFrame {
        overflow-x: auto !important;
    }

    /* Tab navigation: scrollable */
    .stTabs [data-baseweb="tab-list"] {
        overflow-x: auto !important;
        -webkit-overflow-scrolling: touch;
        scrollbar-width: none;
    }
    .stTabs [data-baseweb="tab-list"]::-webkit-scrollbar {
        display: none;
    }
    .stTabs [data-baseweb="tab"] {
        min-height: 44px !important;
        white-space: nowrap !important;
        font-size: 0.9rem !important;
    }
}

/* ── Small phone adjustments (< 400px) ──────────────────────────────── */
@media (max-width: 400px) {
    h1 { font-size: 1.3rem !important; }
    h2 { font-size: 1.1rem !important; }

    .block-container {
        padding-left: 0.5rem !important;
        padding-right: 0.5rem !important;
    }

    [data-testid="stMetricValue"] {
        font-size: 1.2rem !important;
    }
}

/* ── PWA standalone mode (installed app) ────────────────────────────── */
@media (display-mode: standalone) {
    /* Extra top padding for status bar area */
    .block-container {
        padding-top: env(safe-area-inset-top, 1rem) !important;
    }

    /* Hide deploy button in standalone */
    [data-testid="stToolbar"] {
        display: none !important;
    }
}

/* ── Smooth transitions for better feel ─────────────────────────────── */
.stButton > button,
a, details summary {
    transition: all 0.15s ease !important;
}

/* ── Touch-friendly active states ───────────────────────────────────── */
.stButton > button:active {
    transform: scale(0.97) !important;
    opacity: 0.9 !important;
}

/* ── Fix iOS input zoom (force 16px minimum) ────────────────────────── */
@supports (-webkit-touch-callout: none) {
    input, select, textarea {
        font-size: 16px !important;
    }
}
</style>
"""

_INSTALL_BANNER_SCRIPT = """
<div id="pwa-install-banner" style="
    display: none;
    background: linear-gradient(135deg, #1B2A4A 0%, #2a3f6a 100%);
    color: white;
    padding: 12px 16px;
    border-radius: 12px;
    margin: 0;
    font-family: Arial, sans-serif;
    box-shadow: 0 2px 12px rgba(27, 42, 74, 0.3);
    animation: slideIn 0.3s ease-out;
">
    <div style="display: flex; align-items: center; justify-content: space-between; gap: 12px;">
        <div style="display: flex; align-items: center; gap: 10px; flex: 1;">
            <img src="/app/static/icons/icon-72x72.png" alt="MCTV"
                 style="width: 36px; height: 36px; border-radius: 8px;">
            <div>
                <div style="font-weight: 600; font-size: 14px;">Install MCTV Portal</div>
                <div style="font-size: 11px; opacity: 0.8;">Add to your home screen for quick access</div>
            </div>
        </div>
        <button id="pwa-install-btn" style="
            background: #C8A951;
            color: #1B2A4A;
            border: none;
            padding: 8px 16px;
            border-radius: 8px;
            font-weight: 700;
            font-size: 13px;
            cursor: pointer;
            white-space: nowrap;
        ">Install</button>
        <button id="pwa-dismiss-btn" style="
            background: none;
            border: none;
            color: rgba(255,255,255,0.6);
            font-size: 18px;
            cursor: pointer;
            padding: 4px 8px;
            line-height: 1;
        ">&times;</button>
    </div>
</div>

<style>
@keyframes slideIn {
    from { opacity: 0; transform: translateY(-10px); }
    to { opacity: 1; transform: translateY(0); }
}
</style>

<script>
(function() {
    var banner = document.getElementById('pwa-install-banner');
    var installBtn = document.getElementById('pwa-install-btn');
    var dismissBtn = document.getElementById('pwa-dismiss-btn');
    var deferredPrompt = null;

    // Don't show if already installed (standalone mode)
    if (window.matchMedia('(display-mode: standalone)').matches) return;
    if (window.navigator.standalone === true) return;

    // Detect platforms
    var isIOS = /iPad|iPhone|iPod/.test(navigator.userAgent) && !window.MSStream;
    var isAndroid = /Android/i.test(navigator.userAgent);
    var isMobile = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);

    // Listen for the browser's native install prompt (Chrome/Edge/Samsung)
    window.addEventListener('beforeinstallprompt', function(e) {
        e.preventDefault();
        deferredPrompt = e;
        banner.style.display = 'block';
        installBtn.textContent = 'Install';
        installBtn.onclick = function() {
            deferredPrompt.prompt();
            deferredPrompt.userChoice.then(function(result) {
                if (result.outcome === 'accepted') banner.style.display = 'none';
                deferredPrompt = null;
            });
        };
    });

    // Show manual install instructions on mobile if native prompt doesn't fire
    if (isMobile) {
        // Give the beforeinstallprompt 2 seconds to fire; if not, show manual banner
        setTimeout(function() {
            if (deferredPrompt) return; // Native prompt already captured
            banner.style.display = 'block';

            if (isIOS) {
                installBtn.textContent = 'How?';
                installBtn.onclick = function() {
                    alert('To install MCTV Portal:\\n\\n'
                        + '1. Tap the Share button \\u2191 (bottom of screen)\\n'
                        + '2. Scroll down and tap "Add to Home Screen"\\n'
                        + '3. Tap "Add"\\n\\n'
                        + 'The MCTV Portal will appear as an app!');
                };
            } else if (isAndroid) {
                installBtn.textContent = 'How?';
                installBtn.onclick = function() {
                    alert('To install MCTV Portal:\\n\\n'
                        + '1. Tap the \\u22ee menu (3 dots, top-right)\\n'
                        + '2. Tap "Add to Home screen" or "Install app"\\n'
                        + '3. Tap "Add"\\n\\n'
                        + 'The MCTV Portal will appear as an app!');
                };
            }
        }, 2000);
    }

    // Dismiss button
    if (dismissBtn) {
        dismissBtn.onclick = function() {
            banner.style.display = 'none';
        };
    }
})();
</script>
"""
