"""Video Ad Generator — create video ad mockups via Creatomate API."""

import streamlit as st
import os
import sys
import tempfile
from pathlib import Path
from dotenv import load_dotenv

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))
load_dotenv(Path(__file__).parent.parent / ".env", override=True)

st.set_page_config(page_title="Video Ads - MCTV Bot", page_icon="🎬", layout="wide")

from services.auth import check_password
if not check_password():
    st.stop()

from services.config_service import load_config, get_market_names

st.markdown("## Video Ad Generator")
st.caption("Generate professional video ad mockups for clients using Creatomate templates.")

# ── Check API key ─────────────────────────────────────────────────────────────

creatomate_key = os.environ.get("CREATOMATE_API_KEY", "")
if not creatomate_key:
    st.error(
        "CREATOMATE_API_KEY not configured. "
        "Add it to your .env file or set it in Render environment variables."
    )
    st.stop()

from services.creatomate_service import CreatomateService

service = CreatomateService(creatomate_key)

# ── Template Management ───────────────────────────────────────────────────────

st.markdown("### Your Templates")
st.caption("These are the video templates from your Creatomate account.")

# Cache templates for the session
if "creatomate_templates" not in st.session_state:
    st.session_state["creatomate_templates"] = None

if st.button("🔄 Load Templates") or st.session_state["creatomate_templates"] is not None:
    if st.session_state["creatomate_templates"] is None:
        with st.spinner("Fetching templates from Creatomate..."):
            try:
                templates = service.list_templates()
                st.session_state["creatomate_templates"] = templates
            except Exception as e:
                st.error(f"Could not load templates: {e}")
                st.stop()

    templates = st.session_state["creatomate_templates"]

    if not templates:
        st.info(
            "No templates found in your Creatomate account. "
            "Create one at https://creatomate.com/templates"
        )
        st.stop()

    # Show templates as selectable cards
    template_options = {}
    for t in templates:
        name = t.get("name", "Unnamed")
        tid = t.get("id", "")
        created = t.get("created_at", "")[:10]
        label = f"{name} (created {created})"
        template_options[label] = t

    selected_label = st.selectbox(
        "Select Template",
        list(template_options.keys()),
        help="Pick the Creatomate template to use for this video ad.",
    )
    selected_template = template_options[selected_label]
    template_id = selected_template["id"]

    # Show template info
    with st.expander("Template Details"):
        st.code(f"Template ID: {template_id}", language=None)
        st.caption(f"Created: {selected_template.get('created_at', 'Unknown')}")
        tags = selected_template.get("tags", [])
        if tags:
            st.caption(f"Tags: {', '.join(tags)}")

    st.divider()

    # ── Video Generation Form ─────────────────────────────────────────────────

    st.markdown("### Generate Video Ad")

    config = load_config()
    market_names = get_market_names(config)

    col1, col2 = st.columns(2)
    with col1:
        business_name = st.text_input("Business Name *", placeholder="Oxford Floral")
        industry = st.text_input("Industry *", placeholder="Florist / Wedding Flowers")
        city = st.selectbox("City", market_names)
    with col2:
        tagline = st.text_input(
            "Tagline / Headline",
            placeholder="Now Advertising on MCTV in Oxford",
            help="Custom tagline for the video. Leave blank for default.",
        )
        background_url = st.text_input(
            "Background Image URL (optional)",
            placeholder="https://example.com/photo.jpg",
            help="URL of an image to use as the video background.",
        )
        logo_url = st.text_input(
            "Client Logo URL (optional)",
            placeholder="https://example.com/logo.png",
            help="URL of the client's logo.",
        )

    # Advanced: custom modifications
    with st.expander("Advanced: Custom Template Modifications"):
        st.caption(
            "Override any template element directly. Format: one per line as "
            "\"Element-Name.property = value\". These take priority over the fields above."
        )
        custom_mods_text = st.text_area(
            "Custom Modifications",
            height=100,
            placeholder="Title.text = Your Custom Title\nBackground-Image.source = https://example.com/bg.jpg",
        )

    st.divider()

    # Output format
    output_format = st.radio(
        "Output Format",
        ["mp4", "gif"],
        horizontal=True,
        help="MP4 for full quality video, GIF for lightweight social previews.",
    )

    # ── Generate Button ───────────────────────────────────────────────────────

    if st.button("🎬 Generate Video Ad", type="primary", use_container_width=True):
        if not business_name or not industry:
            st.error("Please fill in at least Business Name and Industry.")
        else:
            # Build modifications
            modifications = {}

            # Start with the standard MCTV fields
            from services.creatomate_service import build_mctv_modifications
            modifications = build_mctv_modifications(
                business_name=business_name,
                industry=industry,
                city=city,
                tagline=tagline or None,
                client_logo_url=logo_url or None,
                background_image_url=background_url or None,
            )

            # Layer on any custom modifications
            if custom_mods_text:
                for line in custom_mods_text.strip().split("\n"):
                    line = line.strip()
                    if "=" in line:
                        key, val = line.split("=", 1)
                        modifications[key.strip()] = val.strip()

            # Show what we're sending
            with st.expander("Modifications being sent"):
                st.json(modifications)

            # Render the video
            progress_bar = st.progress(0, text="Starting render...")
            status_text = st.empty()

            def on_progress(status, elapsed):
                if status == "planned":
                    progress_bar.progress(0.1, text="Render queued...")
                elif status in ("rendering", "processing"):
                    pct = min(0.9, 0.1 + (elapsed / 120) * 0.8)
                    progress_bar.progress(pct, text=f"Rendering... ({elapsed}s)")
                status_text.caption(f"Status: {status} | Elapsed: {elapsed}s")

            try:
                result = service.render_video(
                    template_id=template_id,
                    modifications=modifications,
                    output_format=output_format,
                    timeout=180,
                    progress_callback=on_progress,
                )

                progress_bar.progress(1.0, text="Complete!")
                status_text.empty()

                video_url = result.get("url")
                duration = result.get("duration", "?")
                file_size = result.get("file_size", 0)
                file_size_mb = f"{file_size / 1024 / 1024:.1f} MB" if file_size else "?"

                st.success(f"Video generated! Duration: {duration}s | Size: {file_size_mb}")

                # Preview
                if video_url:
                    if output_format == "mp4":
                        st.video(video_url)
                    else:
                        st.image(video_url, caption="Generated GIF")

                    # Download
                    st.markdown(f"**Direct link:** [{video_url}]({video_url})")
                    st.caption("Hosted on Creatomate CDN for 30 days.")

                    # Download to local output folder
                    output_dir = Path(__file__).parent.parent / "output" / "videos"
                    try:
                        local_path = service.download_video(video_url, output_dir)
                        with open(local_path, "rb") as f:
                            st.download_button(
                                f"Download {output_format.upper()}",
                                data=f.read(),
                                file_name=f"MCTV_Ad_{business_name.replace(' ', '_')}.{output_format}",
                                mime=f"video/{output_format}" if output_format == "mp4" else "image/gif",
                                type="primary",
                                use_container_width=True,
                            )
                    except Exception as dl_err:
                        st.warning(f"Could not save locally: {dl_err}")
                        st.markdown(f"You can still download from the link above.")

            except TimeoutError:
                progress_bar.empty()
                status_text.empty()
                st.error("Render timed out after 3 minutes. The video may still be processing — check your Creatomate dashboard.")
            except Exception as e:
                progress_bar.empty()
                status_text.empty()
                st.error(f"Error generating video: {e}")
                st.exception(e)

else:
    st.info("Click **Load Templates** to connect to your Creatomate account and see available video templates.")
