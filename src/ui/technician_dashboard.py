import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from src.database.ticket_db import TicketDB

# --- Technician Dashboard Pages ---
def technician_dashboard_page():
    st.title("🔧 Technician Dashboard")

    # Get current technician info from session
    tech_info = st.session_state.get('technician', {})
    tech_name = tech_info.get('name', 'Unknown')
    tech_id = tech_info.get('id', 'Unknown')

    # For demo purposes, map technician ID to email
    tech_email_map = {
        'T101': 'technician1@company.com',
        'T102': 'technician2@company.com',
        'T103': 'technician3@company.com',
        'T104': 'technician4@company.com'
    }
    tech_email = tech_email_map.get(tech_id, f"{tech_name.lower()}@company.com")

    st.markdown(f"**Welcome, {tech_name}!**")
    st.caption(f"Tech ID: {tech_id} | Email: {tech_email}")
    st.markdown("---")

    # Get tickets from database
    try:
        ticket_db = TicketDB()
        my_tickets = ticket_db.get_tickets_for_technician(tech_email)
        if not my_tickets:
            my_tickets = []
    except Exception as e:
        st.error(f"Error loading tickets: {e}")
        my_tickets = []

    # --- Metrics ---
    total_tickets = len(my_tickets)
    urgent_count = sum(1 for t in my_tickets if 'Critical' in str(t.get('ISSUETYPE', '')) or 'Critical' in str(t.get('TICKETTYPE', '')))
    overdue_count = sum(1 for t in my_tickets if t.get('DUEDATETIME') and t.get('DUEDATETIME') < datetime.now().strftime('%Y-%m-%d'))
    total_today = sum(1 for t in my_tickets if str(t.get('DUEDATETIME', '')).startswith(datetime.now().strftime('%Y-%m-%d')))

    # Since we don't have status in the new schema, we'll show different metrics
    assigned_count = total_tickets
    in_progress_count = 0  # Would need status field
    completed_count = 0    # Would need status field
    completion_rate = 0    # Would need status field
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Total Assigned", assigned_count)
    col2.metric("Urgent", urgent_count)
    col3.metric("Overdue", overdue_count)
    col4.metric("Today's Tickets", total_today)
    col5.metric("This Week", total_tickets)  # Simplified for now
    st.markdown("---")

    # --- Urgent Tickets ---
    st.subheader("🚨 Urgent Tickets")
    urgent_tickets = [t for t in my_tickets if 'Critical' in str(t.get('ISSUETYPE', '')) or 'Critical' in str(t.get('TICKETTYPE', ''))]
    if urgent_tickets:
        for i, t in enumerate(urgent_tickets):
            with st.expander(f"🚨 {t.get('TICKETNUMBER', 'N/A')} - {t.get('TITLE', '')}", expanded=False):
                st.markdown(f"**Issue Type:** {t.get('ISSUETYPE', '')}")
                st.markdown(f"**Ticket Type:** {t.get('TICKETTYPE', '')}")
                st.markdown(f"**Due Date:** {t.get('DUEDATETIME', '')}")
                st.markdown(f"**Description:** {t.get('DESCRIPTION', '')}")
                st.markdown(f"**User:** {t.get('USEREMAIL', '')}")
                st.markdown(f"**Phone:** {t.get('PHONENUMBER', '')}")

                # Display resolution if available
                if t.get('RESOLUTION'):
                    with st.expander("🔧 Resolution Notes", expanded=False):
                        st.markdown(t.get('RESOLUTION', ''))

                # Action buttons (simplified since no status field)
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("📞 Contact User", key=f"contact_urgent_{i}"):
                        st.info(f"Contact user at: {t.get('USEREMAIL', '')} or {t.get('PHONENUMBER', '')}")
                with col2:
                    if st.button("📝 Add Note", key=f"note_urgent_{i}"):
                        st.session_state[f'note_modal_{t.get("TICKETNUMBER", i)}'] = True

                # Note modal
                if st.session_state.get(f'note_modal_{t.get("TICKETNUMBER", i)}', False):
                    note = st.text_area("Add Work Note:", key=f'note_text_urgent_{i}')
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("Save Note", key=f'save_note_urgent_{i}'):
                            # Here you would save to database
                            st.session_state[f'note_modal_{t.get("TICKETNUMBER", i)}'] = False
                            st.success("Note would be saved to database.")
                            st.rerun()
                    with col2:
                        if st.button("Cancel", key=f'cancel_note_urgent_{i}'):
                            st.session_state[f'note_modal_{t.get("TICKETNUMBER", i)}'] = False
                            st.rerun()
    else:
        st.info("No urgent tickets assigned.")
    st.markdown("---")

    # --- All Assigned Tickets ---
    st.subheader("📋 All Assigned Tickets")
    regular_tickets = [t for t in my_tickets if not ('Critical' in str(t.get('ISSUETYPE', '')) or 'Critical' in str(t.get('TICKETTYPE', '')))]
    if regular_tickets:
        for i, t in enumerate(regular_tickets):
            with st.expander(f"📋 {t.get('TICKETNUMBER', 'N/A')} - {t.get('TITLE', '')}", expanded=False):
                st.markdown(f"**Issue Type:** {t.get('ISSUETYPE', '')}")
                st.markdown(f"**Ticket Type:** {t.get('TICKETTYPE', '')}")
                st.markdown(f"**Due Date:** {t.get('DUEDATETIME', '')}")
                st.markdown(f"**User:** {t.get('USEREMAIL', '')}")
                st.markdown(f"**Phone:** {t.get('PHONENUMBER', '')}")

                # Display resolution if available
                if t.get('RESOLUTION'):
                    with st.expander("🔧 Resolution Notes", expanded=False):
                        st.markdown(t.get('RESOLUTION', ''))

                # Action buttons
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("📞 Contact User", key=f"contact_regular_{i}"):
                        st.info(f"Contact user at: {t.get('USEREMAIL', '')} or {t.get('PHONENUMBER', '')}")
                with col2:
                    if st.button("📝 Add Note", key=f"note_regular_{i}"):
                        st.session_state[f'note_modal_reg_{t.get("TICKETNUMBER", i)}'] = True
                st.markdown(f"**Status:** {t.get('status', '')}")
                st.markdown(f"**Due Date:** {t.get('due_date', '')}")
                st.markdown(f"**Description:** {t.get('description', '')}")
                if t.get('status', '').lower() in ['assigned', 'open']:
                    if st.button("▶️ Start Work", key=f"startwork_assigned_{i}"):
                        t['status'] = 'In Progress'
                        st.success("Status updated to In Progress")
                        st.rerun()
                if st.button("📝 Add Note", key=f"note_assigned_{i}"):
                    st.session_state[f'note_modal_{t.get("ticket_number", i)}'] = True
                if st.session_state.get(f'note_modal_{t.get("ticket_number", i)}', False):
                    note = st.text_area("Add Work Note:", key=f'note_text_assigned_{i}')
                    if st.button("Save Note", key=f'save_note_assigned_{i}'):
                        t.setdefault('work_notes', []).append({'note': note, 'time': datetime.now().isoformat()})
                        st.session_state[f'note_modal_{t.get("ticket_number", i)}'] = False
                        st.success("Note added.")
                        st.rerun()
                    if st.button("Cancel", key=f'cancel_note_assigned_{i}'):
                        st.session_state[f'note_modal_{t.get("ticket_number", i)}'] = False
    else:
        st.info("No assigned tickets.")
    st.markdown("---")
    # --- In Progress Tickets ---
    st.subheader("⚡ In Progress Tickets")
    inprogress_tickets = [t for t in my_tickets if t.get('status', '').lower() == 'in progress']
    if inprogress_tickets:
        for i, t in enumerate(inprogress_tickets):
            with st.expander(f"⚡ {t.get('ticket_number', 'N/A')} - {t.get('title', '')}", expanded=False):
                st.markdown(f"**Priority:** {t.get('priority', '')}")
                st.markdown(f"**Status:** {t.get('status', '')}")
                st.markdown(f"**Due Date:** {t.get('due_date', '')}")
                st.markdown(f"**Description:** {t.get('description', '')}")
                if t.get('status', '').lower() == 'in progress':
                    if st.button("✅ Mark Resolved", key=f"resolve_inprogress_{i}"):
                        t['status'] = 'Resolved'
                        st.success("Status updated to Resolved")
                        st.rerun()
                if st.button("📝 Add Note", key=f"note_inprogress_{i}"):
                    st.session_state[f'note_modal_{t.get("ticket_number", i)}'] = True
                if st.session_state.get(f'note_modal_{t.get("ticket_number", i)}', False):
                    note = st.text_area("Add Work Note:", key=f'note_text_inprogress_{i}')
                    if st.button("Save Note", key=f'save_note_inprogress_{i}'):
                        t.setdefault('work_notes', []).append({'note': note, 'time': datetime.now().isoformat()})
                        st.session_state[f'note_modal_{t.get("ticket_number", i)}'] = False
                        st.success("Note added.")
                        st.rerun()
                    if st.button("Cancel", key=f'cancel_note_inprogress_{i}'):
                        st.session_state[f'note_modal_{t.get("ticket_number", i)}'] = False
    else:
        st.info("No tickets in progress.")

def technician_my_tickets_page():
    st.title("📋 My Tickets")

    # Get current technician info from session
    tech_info = st.session_state.get('technician', {})
    tech_name = tech_info.get('name', 'Unknown')
    tech_id = tech_info.get('id', 'Unknown')

    # For demo purposes, map technician ID to email
    tech_email_map = {
        'T101': 'technician1@company.com',
        'T102': 'technician2@company.com',
        'T103': 'technician3@company.com',
        'T104': 'technician4@company.com'
    }
    tech_email = tech_email_map.get(tech_id, f"{tech_name.lower()}@company.com")

    st.markdown(f"**Technician:** {tech_name} ({tech_email})")
    st.markdown("---")

    kb_data = load_kb_data()
    # Filter tickets assigned to this technician
    my_tickets = [entry['new_ticket'] for entry in kb_data if entry['new_ticket'].get('assignment_result', {}).get('technician_email') == tech_email]
    # Filters
    status_options = sorted(set(t.get('status', 'Assigned') for t in my_tickets))
    priority_options = sorted(set(t.get('priority', 'Medium') for t in my_tickets))
    category_options = sorted(set(t.get('category', 'General') for t in my_tickets))
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        status_filter = st.multiselect("Status", options=status_options, default=status_options)
    with col2:
        priority_filter = st.multiselect("Priority", options=priority_options, default=priority_options)
    with col3:
        category_filter = st.multiselect("Category", options=category_options, default=category_options)
    with col4:
        sort_option = st.selectbox("Sort By", options=["Newest", "Oldest", "Priority", "Status"])
    # Apply filters
    filtered_tickets = [t for t in my_tickets if t.get('status', 'Assigned') in status_filter and t.get('priority', 'Medium') in priority_filter and t.get('category', 'General') in category_filter]
    # Sort
    if sort_option == "Newest":
        filtered_tickets = sorted(filtered_tickets, key=lambda t: (t.get('date', ''), t.get('time', '')), reverse=True)
    elif sort_option == "Oldest":
        filtered_tickets = sorted(filtered_tickets, key=lambda t: (t.get('date', ''), t.get('time', '')))
    elif sort_option == "Priority":
        priority_order = {"Critical": 1, "Desktop/User Down": 2, "High": 3, "Medium": 4, "Low": 5}
        filtered_tickets = sorted(filtered_tickets, key=lambda t: priority_order.get(t.get('priority', 'Medium'), 99))
    elif sort_option == "Status":
        status_order = {"Assigned": 1, "Open": 2, "In Progress": 3, "Resolved": 4, "Closed": 5}
        filtered_tickets = sorted(filtered_tickets, key=lambda t: status_order.get(t.get('status', 'Assigned'), 99))
    st.markdown(f"**{len(filtered_tickets)} tickets found.**")
    # --- Bulk selection state ---
    if 'bulk_selected_tickets' not in st.session_state:
        st.session_state.bulk_selected_tickets = set()
    # Select All checkbox
    select_all = st.checkbox("Select All", value=False, key="select_all_my_tickets")
    # Ticket checkboxes
    ticket_keys = []
    for i, t in enumerate(filtered_tickets):
        ticket_key = f"ticket_checkbox_{t.get('ticket_number', i)}"
        ticket_keys.append(ticket_key)
        checked = select_all or (ticket_key in st.session_state.bulk_selected_tickets)
        if st.checkbox(f"Select {t.get('ticket_number', 'N/A')} - {t.get('title', '')}", value=checked, key=ticket_key):
            st.session_state.bulk_selected_tickets.add(ticket_key)
        else:
            st.session_state.bulk_selected_tickets.discard(ticket_key)
    # Bulk action bar
    selected_indices = [i for i, t in enumerate(filtered_tickets) if f"ticket_checkbox_{t.get('ticket_number', i)}" in st.session_state.bulk_selected_tickets]
    if selected_indices:
        st.markdown(f"**Bulk Actions for {len(selected_indices)} selected tickets:**")
        colA, colB, colC = st.columns(3)
        with colA:
            if st.button("▶️ Bulk Start Work"):
                for idx in selected_indices:
                    t = filtered_tickets[idx]
                    if t.get('status', '').lower() in ['assigned', 'open']:
                        t['status'] = 'In Progress'
                save_kb_data(kb_data)
                st.success("Bulk status updated to In Progress")
                st.session_state.bulk_selected_tickets.clear()
                st.rerun()
        with colB:
            if st.button("✅ Bulk Mark Resolved"):
                for idx in selected_indices:
                    t = filtered_tickets[idx]
                    if t.get('status', '').lower() == 'in progress':
                        t['status'] = 'Resolved'
                save_kb_data(kb_data)
                st.success("Bulk status updated to Resolved")
                st.session_state.bulk_selected_tickets.clear()
                st.rerun()
        with colC:
            if st.button("📝 Bulk Add Note"):
                st.session_state.bulk_note_modal = True
    if st.session_state.get('bulk_note_modal', False) and selected_indices:
        note = st.text_area("Bulk Add Work Note:", key='bulk_note_text')
        if st.button("Save Bulk Note"):
            for idx in selected_indices:
                t = filtered_tickets[idx]
                t.setdefault('work_notes', []).append({'note': note, 'time': datetime.now().isoformat()})
            save_kb_data(kb_data)
            st.success("Bulk note added.")
            st.session_state.bulk_note_modal = False
            st.session_state.bulk_selected_tickets.clear()
            st.rerun()
        if st.button("Cancel Bulk Note"):
            st.session_state.bulk_note_modal = False
    # Individual ticket actions
    for i, t in enumerate(filtered_tickets):
        with st.expander(f"{t.get('ticket_number', 'N/A')} - {t.get('title', '')}", expanded=False):
            st.markdown(f"**Priority:** {t.get('priority', '')}")
            st.markdown(f"**Status:** {t.get('status', '')}")
            st.markdown(f"**Due Date:** {t.get('due_date', '')}")
            st.markdown(f"**Description:** {t.get('description', '')}")
            # Action: Start Work
            if t.get('status', '').lower() in ['assigned', 'open']:
                if st.button("▶️ Start Work", key=f"startwork_my_{i}"):
                    t['status'] = 'In Progress'
                    save_kb_data(kb_data)
                    st.success("Status updated to In Progress")
                    st.rerun()
            # Action: Mark Resolved
            if t.get('status', '').lower() == 'in progress':
                if st.button("✅ Mark Resolved", key=f"resolve_my_{i}"):
                    t['status'] = 'Resolved'
                    save_kb_data(kb_data)
                    st.success("Status updated to Resolved")
                    st.rerun()
            # Add Note
            if st.button("📝 Add Note", key=f"note_my_{i}"):
                st.session_state[f'note_modal_my_{t.get("ticket_number", i)}'] = True
            if st.session_state.get(f'note_modal_my_{t.get("ticket_number", i)}', False):
                note = st.text_area("Add Work Note:", key=f'note_text_my_{i}')
                if st.button("Save Note", key=f'save_note_my_{i}'):
                    t.setdefault('work_notes', []).append({'note': note, 'time': datetime.now().isoformat()})
                    save_kb_data(kb_data)
                    st.session_state[f'note_modal_my_{t.get("ticket_number", i)}'] = False
                    st.success("Note added.")
                    st.rerun()
                if st.button("Cancel", key=f'cancel_note_my_{i}'):
                    st.session_state[f'note_modal_my_{t.get("ticket_number", i)}'] = False
            # Call/Email User
            requester_phone = t.get('requester_phone') or t.get('user_phone')
            requester_email = t.get('requester_email') or t.get('user_email')
            if requester_phone:
                st.markdown(f"**📞 Call User:** {requester_phone}")
            if requester_email:
                st.markdown(f"**✉️ Email User:** {requester_email}")
            # Show work notes history
            if t.get('work_notes'):
                st.markdown("**Work Notes History:**")
                for note in t['work_notes']:
                    st.info(f"{note['note']} ({note['time']})")

def technician_urgent_tickets_page():
    st.title("🚨 Urgent Tickets")

    # Get current technician info from session
    tech_info = st.session_state.get('technician', {})
    tech_name = tech_info.get('name', 'Unknown')
    tech_id = tech_info.get('id', 'Unknown')

    # For demo purposes, map technician ID to email
    tech_email_map = {
        'T101': 'technician1@company.com',
        'T102': 'technician2@company.com',
        'T103': 'technician3@company.com',
        'T104': 'technician4@company.com'
    }
    tech_email = tech_email_map.get(tech_id, f"{tech_name.lower()}@company.com")

    st.markdown(f"**Technician:** {tech_name} ({tech_email})")
    st.markdown("---")

    kb_data = load_kb_data()
    # Filter urgent tickets assigned to this technician
    urgent_tickets = [entry['new_ticket'] for entry in kb_data if entry['new_ticket'].get('assignment_result', {}).get('technician_email') == tech_email and entry['new_ticket'].get('priority') in ['Critical', 'Desktop/User Down'] and entry['new_ticket'].get('status', '').lower() not in ['resolved', 'closed']]
    st.markdown(f"**{len(urgent_tickets)} urgent tickets found.**")
    for i, t in enumerate(urgent_tickets):
        with st.expander(f"🚨 {t.get('ticket_number', 'N/A')} - {t.get('title', '')}", expanded=False):
            st.markdown(f"**Priority:** {t.get('priority', '')}")
            st.markdown(f"**Status:** {t.get('status', '')}")
            st.markdown(f"**Due Date:** {t.get('due_date', '')}")
            st.markdown(f"**Description:** {t.get('description', '')}")
            # Action: Start Immediately
            if t.get('status', '').lower() in ['assigned', 'open']:
                if st.button("⚡ Start Immediately", key=f"startimmediate_urgent_{i}"):
                    t['status'] = 'In Progress'
                    st.success("Status updated to In Progress")
                    st.rerun()
            # Action: Mark Resolved
            if t.get('status', '').lower() == 'in progress':
                if st.button("✅ Mark Resolved", key=f"resolve_urgentpage_{i}"):
                    t['status'] = 'Resolved'
                    st.success("Status updated to Resolved")
                    st.rerun()
            # Add Note
            if st.button("📝 Add Note", key=f"note_urgentpage_{i}"):
                st.session_state[f'note_modal_urgentpage_{t.get("ticket_number", i)}'] = True
            if st.session_state.get(f'note_modal_urgentpage_{t.get("ticket_number", i)}', False):
                note = st.text_area("Add Work Note:", key=f'note_text_urgentpage_{i}')
                if st.button("Save Note", key=f'save_note_urgentpage_{i}'):
                    t.setdefault('work_notes', []).append({'note': note, 'time': datetime.now().isoformat()})
                    st.session_state[f'note_modal_urgentpage_{t.get("ticket_number", i)}'] = False
                    st.success("Note added.")
                    st.rerun()
                if st.button("Cancel", key=f'cancel_note_urgentpage_{i}'):
                    st.session_state[f'note_modal_urgentpage_{t.get("ticket_number", i)}'] = False
            # Emergency contact info
            st.markdown("---")
            st.markdown("**🚨 Emergency Contact:**")
            st.markdown("📞 9723100860 | ✉️ inquire@64-squares.com")

def technician_analytics_page():
    st.title("📊 Technician Analytics")

    # Get current technician info from session
    tech_info = st.session_state.get('technician', {})
    tech_name = tech_info.get('name', 'Unknown')
    tech_id = tech_info.get('id', 'Unknown')

    # For demo purposes, map technician ID to email
    tech_email_map = {
        'T101': 'technician1@company.com',
        'T102': 'technician2@company.com',
        'T103': 'technician3@company.com',
        'T104': 'technician4@company.com'
    }
    tech_email = tech_email_map.get(tech_id, f"{tech_name.lower()}@company.com")

    st.markdown(f"**Technician:** {tech_name} ({tech_email})")
    st.markdown("---")

    kb_data = load_kb_data()
    # Filter tickets assigned to this technician
    my_tickets = [entry['new_ticket'] for entry in kb_data if entry['new_ticket'].get('assignment_result', {}).get('technician_email') == tech_email]
    # Time period selector
    period = st.selectbox("Time Period", options=["Last 7 days", "Last 30 days", "Last 90 days", "All Time"])
    now = datetime.now()
    if period == "Last 7 days":
        cutoff = now - timedelta(days=7)
    elif period == "Last 30 days":
        cutoff = now - timedelta(days=30)
    elif period == "Last 90 days":
        cutoff = now - timedelta(days=90)
    else:
        cutoff = datetime.min
    filtered = []
    for t in my_tickets:
        try:
            created_time = datetime.fromisoformat(t.get('date', '') + 'T' + t.get('time', ''))
            if created_time >= cutoff:
                filtered.append(t)
        except:
            continue
    # Metrics
    total = len(filtered)
    resolved = sum(1 for t in filtered if t.get('status', '').lower() in ['resolved', 'closed'])
    in_progress = sum(1 for t in filtered if t.get('status', '').lower() == 'in progress')
    assigned = sum(1 for t in filtered if t.get('status', '').lower() in ['assigned', 'open'])
    completion_rate = int((resolved / total) * 100) if total else 0
    # Avg resolution time (if timestamps available)
    resolution_times = []
    for t in filtered:
        if t.get('status', '').lower() in ['resolved', 'closed']:
            try:
                created_time = datetime.fromisoformat(t.get('date', '') + 'T' + t.get('time', ''))
                resolved_time = created_time
                if t.get('resolved_time'):
                    resolved_time = datetime.fromisoformat(t['resolved_time'])
                elif t.get('updated_time'):
                    resolved_time = datetime.fromisoformat(t['updated_time'])
                resolution_times.append((resolved_time - created_time).total_seconds())
            except:
                continue
    avg_resolution_time = (sum(resolution_times) / len(resolution_times) / 3600) if resolution_times else 0
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total", total)
    col2.metric("Resolved", resolved)
    col3.metric("Completion Rate", f"{completion_rate}%")
    col4.metric("Avg Resolution Time (hrs)", f"{avg_resolution_time:.2f}")
    # Charts
    st.markdown("---")
    st.subheader("Tickets by Status")
    status_counts = {}
    for t in filtered:
        status = t.get('status', 'Assigned')
        status_counts[status] = status_counts.get(status, 0) + 1
    if status_counts:
        df_status = pd.DataFrame({"Status": list(status_counts.keys()), "Count": list(status_counts.values())})
        fig = pd.DataFrame(df_status).plot.pie(y="Count", labels=df_status["Status"], legend=False, autopct='%1.1f%%')
        st.pyplot(fig.get_figure())
    st.subheader("Tickets by Priority")
    priority_counts = {}
    for t in filtered:
        priority = t.get('priority', 'Medium')
        priority_counts[priority] = priority_counts.get(priority, 0) + 1
    if priority_counts:
        df_priority = pd.DataFrame({"Priority": list(priority_counts.keys()), "Count": list(priority_counts.values())})
        fig = pd.DataFrame(df_priority).plot.bar(x="Priority", y="Count")
        st.pyplot(fig.get_figure())
    st.subheader("Daily Trends")
    daily_counts = {}
    for t in filtered:
        d = t.get('date', '')
        if d:
            daily_counts[d] = daily_counts.get(d, 0) + 1
    if daily_counts:
        df_daily = pd.DataFrame({"Date": list(daily_counts.keys()), "Count": list(daily_counts.values())})
        df_daily = df_daily.sort_values("Date")
        fig = pd.DataFrame(df_daily).plot.line(x="Date", y="Count")
        st.pyplot(fig.get_figure()) 