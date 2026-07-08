# Copyright (c) 2026 MCTV Digital, Inc. All rights reserved.
# Proprietary and confidential.
"""Tasks — Streamlit page for the MCTV Team Member portal.

Add, view, filter, and manage tasks. Pairs with the daily email cron
that lands a personalized summary in each member's inbox at 7 AM CT
on weekdays.

Drop into: mctv-bot/pages/23_Tasks.py
"""
import html
import os
import sys
from datetime import date, timedelta
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent.parent))
load_dotenv(Path(__file__).parent.parent / ".env", override=True)

from services.auth import check_password
from services.task_service import (
    create_task,
    mark_done,
    snooze,
    reassign,
    list_for_member,
    list_group,
    list_overdue,
    list_upcoming,
    unsnooze_due,
    local_today,
)

st.set_page_config(
    page_title="Tasks - MCTV Bot",
    page_icon="\U0001F3AF",
    layout="wide",
)

if not check_password():
    st.stop()

from services.team_ui import render_team_sidebar
render_team_sidebar()

# Wake any snoozed tasks whose date has arrived
try:
    unsnooze_due()
except Exception:  # noqa: BLE001 — never block the page on maintenance
    pass

TEAM = ["Creed", "Mary", "Swayze", "Jagger", "Elliot"]


st.markdown("## \U0001F3AF Tasks")
st.caption(
    "Your daily task list — plus group tasks the whole team can pick up. "
    "Daily summary lands in your inbox every weekday at 7 AM CT."
)

# The team portal uses a shared password (no per-user login), so pick who
# you are here. Assignments and the daily email match on this first name.
viewing_as = st.selectbox("Viewing as", TEAM, key="tasks_viewing_as")
tm_id = viewing_as


with st.expander("+ Add a task", expanded=False):
    with st.form("new_task", clear_on_submit=True):
        title = st.text_input("Title", placeholder="What needs to happen?")
        col1, col2, col3 = st.columns(3)
        with col1:
            priority = st.selectbox("Priority", ["low", "normal", "high", "urgent"], index=1)
        with col2:
            due = st.date_input("Due date", value=local_today())
        with col3:
            team_options = ["(group task)"] + TEAM
            assignee_display = st.selectbox("Assign to", team_options)
        description = st.text_area("Description (optional)", height=80)
        submitted = st.form_submit_button("Create task", type="primary")
        if submitted:
            if not title.strip():
                st.warning("Title is required.")
            else:
                assigned = None if assignee_display == "(group task)" else assignee_display
                # NB: no st.rerun() inside this try — RerunException subclasses
                # Exception and would be swallowed as a bogus error. The task
                # lists below are fetched later in this same run, so the new
                # task appears without a rerun anyway.
                try:
                    create_task(
                        title=title.strip(),
                        description=description.strip() or None,
                        assigned_to=assigned,
                        priority=priority,
                        due_date=due,
                        created_by=tm_id,
                    )
                except Exception as e:
                    st.error(f"Could not create task: {e}")
                else:
                    st.success("Task created.")


tab_today, tab_my, tab_group, tab_overdue, tab_week = st.tabs([
    "\U0001F4CB Today",
    "\U0001F464 My tasks",
    "\U0001F465 Group",
    "\U0001F525 Overdue",
    "\U0001F4C5 This week",
])


def _task_action(fn, *args) -> bool:
    try:
        fn(*args)
        return True
    except Exception as e:  # noqa: BLE001
        st.error(f"Could not update task: {e}")
        return False


def _render_task_card(t, key_prefix):
    pri_color = {"urgent": "#C00000", "high": "#ED7D31", "normal": "#1F3864", "low": "#888"}.get(
        t.get("priority", "normal"), "#1F3864"
    )
    pri_badge = (t.get("priority", "normal") or "normal").upper()
    # title is rendered inside unsafe_allow_html markdown — escape it
    title = html.escape(str(t.get("title", "(no title)")))
    due = t.get("due_date") or "no due date"
    assignee = t.get("assigned_to") or "(group)"
    source = t.get("source", "manual")
    src_badge = "" if source == "manual" else f' · {source}'

    col_main, col_action = st.columns([5, 1])
    with col_main:
        st.markdown(
            f"**{title}**  \n"
            f"<span style='color:{pri_color}; font-size:12px; font-weight:600;'>{pri_badge}</span>"
            f" · due {due} · {assignee}{src_badge}",
            unsafe_allow_html=True,
        )
        if t.get("description"):
            st.caption(t["description"])
    with col_action:
        # key_prefix keeps widget keys unique when the same task shows in
        # more than one tab (Today / My tasks / This week all overlap).
        # st.rerun() stays OUTSIDE the try (see _task_action) so it isn't
        # swallowed as an exception.
        if st.button("Done", key=f"done_{key_prefix}_{t['id']}", type="secondary"):
            if _task_action(mark_done, t["id"]):
                st.rerun()
        if st.button("Snooze 1d", key=f"snooze_{key_prefix}_{t['id']}"):
            if _task_action(snooze, t["id"], local_today() + timedelta(days=1)):
                st.rerun()
        if not t.get("assigned_to"):
            if st.button("Claim", key=f"claim_{key_prefix}_{t['id']}"):
                if _task_action(reassign, t["id"], tm_id):
                    st.rerun()


def _render_list(tasks, empty_msg="Nothing here.", key_prefix="list"):
    if not tasks:
        st.caption(empty_msg)
        return
    for t in tasks:
        with st.container(border=True):
            _render_task_card(t, key_prefix)


with tab_today:
    today_iso = local_today().isoformat()
    today_mine = [t for t in list_for_member(tm_id) if t.get("due_date") == today_iso]
    today_group = [t for t in list_group() if t.get("due_date") == today_iso]
    st.subheader("Yours due today")
    _render_list(today_mine, "Nothing due today for you.", key_prefix="today_mine")
    st.subheader("Group tasks due today")
    _render_list(today_group, "Nothing for the team today.", key_prefix="today_grp")

with tab_my:
    _render_list(list_for_member(tm_id), "No pending tasks assigned to you.", key_prefix="mine")

with tab_group:
    _render_list(list_group(), "No group tasks pending.", key_prefix="grp")

with tab_overdue:
    _render_list(list_overdue(tm_id), "Nothing overdue — clean slate.", key_prefix="over")

with tab_week:
    _render_list(list_upcoming(tm_id, days=7), "Nothing on the schedule this week.", key_prefix="week")
