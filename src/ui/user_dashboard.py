"""
User Dashboard Components
Contains user-specific dashboard pages and functionality.
"""

import streamlit as st
import json
import os
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
from collections import Counter
from typing import List, Dict

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from config import *


def load_kb_data():
    """Load knowledgebase data."""
    try:
        if os.path.exists('Knowledgebase.json'):
            with open('Knowledgebase.json', 'r') as f:
                return json.load(f)
        return []
    except Exception as e:
        st.error(f"Error loading knowledgebase: {e}")
        return []


def user_my_tickets_page():
    """Show tickets submitted by the current user."""
    st.title("📋 My Tickets")
    
    user_info = st.session_state.get('user', {})
    user_id = user_info.get('id', '')
    user_name = user_info.get('name', '')
    
    st.markdown(f"**User:** {user_name} ({user_id})")
    st.markdown("---")
    
    kb_data = load_kb_data()
    
    # Filter tickets by current user (assuming user_id is stored in ticket data)
    # For now, we'll show all tickets since the current data structure doesn't have user association
    # In a real implementation, you'd filter by user_id
    user_tickets = []
    for entry in kb_data:
        ticket = entry.get('new_ticket', {})
        # Add user association logic here when available
        # For demo purposes, showing all tickets
        user_tickets.append(ticket)
    
    if not user_tickets:
        st.info("You haven't submitted any tickets yet.")
        if st.button("Submit New Ticket"):
            st.session_state.page = "main"
            st.rerun()
        return
    
    # Filters
    status_options = sorted(set(t.get('status', 'Open') for t in user_tickets))
    priority_options = sorted(set(t.get('priority', 'Medium') for t in user_tickets))
    
    col1, col2, col3 = st.columns(3)
    with col1:
        status_filter = st.multiselect("Status", options=status_options, default=status_options)
    with col2:
        priority_filter = st.multiselect("Priority", options=priority_options, default=priority_options)
    with col3:
        date_filter = st.date_input("From Date", value=datetime.now() - timedelta(days=30))
    
    # Apply filters
    filtered_tickets = []
    for ticket in user_tickets:
        if (ticket.get('status', 'Open') in status_filter and 
            ticket.get('priority', 'Medium') in priority_filter):
            try:
                ticket_date = datetime.strptime(ticket.get('date', ''), '%Y-%m-%d').date()
                if ticket_date >= date_filter:
                    filtered_tickets.append(ticket)
            except:
                filtered_tickets.append(ticket)  # Include if date parsing fails
    
    st.markdown(f"**{len(filtered_tickets)} tickets found**")
    
    # Display tickets
    for i, ticket in enumerate(filtered_tickets):
        with st.expander(f"🎫 {ticket.get('ticket_number', 'N/A')} - {ticket.get('title', 'No Title')}", expanded=False):
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"**Status:** {ticket.get('status', 'Open')}")
                st.markdown(f"**Priority:** {ticket.get('priority', 'Medium')}")
                st.markdown(f"**Category:** {ticket.get('category', 'General')}")
            with col2:
                st.markdown(f"**Date:** {ticket.get('date', 'N/A')}")
                st.markdown(f"**Due Date:** {ticket.get('due_date', 'N/A')}")
                assignment = ticket.get('assignment_result', {})
                st.markdown(f"**Assigned To:** {assignment.get('assigned_technician', 'Unassigned')}")
            
            st.markdown(f"**Description:** {ticket.get('description', 'No description')}")
            
            # Show resolution if available
            if ticket.get('status', '').lower() in ['resolved', 'closed']:
                st.markdown("**Resolution:**")
                st.info(ticket.get('resolution', 'No resolution provided'))


def user_ticket_status_page():
    """Show ticket status tracking for user."""
    st.title("📊 Ticket Status")
    
    user_info = st.session_state.get('user', {})
    user_name = user_info.get('name', '')
    
    st.markdown(f"**User:** {user_name}")
    st.markdown("---")
    
    kb_data = load_kb_data()
    
    # Get user tickets (for demo, showing all)
    user_tickets = [entry.get('new_ticket', {}) for entry in kb_data]
    
    if not user_tickets:
        st.info("No tickets found.")
        return
    
    # Status summary
    status_counts = Counter(t.get('status', 'Open') for t in user_tickets)
    priority_counts = Counter(t.get('priority', 'Medium') for t in user_tickets)
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Tickets", len(user_tickets))
    with col2:
        st.metric("Open", status_counts.get('Open', 0) + status_counts.get('Assigned', 0))
    with col3:
        st.metric("In Progress", status_counts.get('In Progress', 0))
    with col4:
        st.metric("Resolved", status_counts.get('Resolved', 0) + status_counts.get('Closed', 0))
    
    st.markdown("---")
    
    # Charts
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Status Distribution")
        if status_counts:
            status_df = pd.DataFrame(list(status_counts.items()), columns=['Status', 'Count'])
            fig = px.pie(status_df, values='Count', names='Status', title="Ticket Status")
            st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.subheader("Priority Distribution")
        if priority_counts:
            priority_df = pd.DataFrame(list(priority_counts.items()), columns=['Priority', 'Count'])
            fig = px.bar(priority_df, x='Priority', y='Count', title="Ticket Priority")
            st.plotly_chart(fig, use_container_width=True)
    
    # Recent activity
    st.subheader("Recent Tickets")
    recent_tickets = sorted(user_tickets, key=lambda x: x.get('date', ''), reverse=True)[:5]
    
    for ticket in recent_tickets:
        with st.container():
            col1, col2, col3, col4 = st.columns([3, 2, 2, 2])
            with col1:
                st.markdown(f"**{ticket.get('ticket_number', 'N/A')}** - {ticket.get('title', 'No Title')}")
            with col2:
                status = ticket.get('status', 'Open')
                if status.lower() in ['resolved', 'closed']:
                    st.success(status)
                elif status.lower() == 'in progress':
                    st.warning(status)
                else:
                    st.info(status)
            with col3:
                priority = ticket.get('priority', 'Medium')
                if priority in ['Critical', 'High']:
                    st.error(priority)
                elif priority == 'Medium':
                    st.warning(priority)
                else:
                    st.success(priority)
            with col4:
                st.text(ticket.get('date', 'N/A'))
            st.markdown("---")


def user_help_page():
    """Show help and support information for users."""
    st.title("❓ Help & Support")
    
    st.markdown("""
    ## How to Submit a Ticket
    
    1. **Go to Home** - Click on the "🏠 Home" button in the sidebar
    2. **Fill out the form** - Provide a clear title and detailed description
    3. **Select priority** - Choose the appropriate priority level
    4. **Submit** - Click the "Submit Ticket" button
    
    ## Ticket Priorities
    
    - **🔴 Critical** - System down, major functionality broken
    - **🟠 High** - Important feature not working, affects multiple users
    - **🟡 Medium** - Minor issues, workarounds available
    - **🟢 Low** - Enhancement requests, cosmetic issues
    
    ## Ticket Status Meanings
    
    - **Open** - Ticket submitted, waiting for assignment
    - **Assigned** - Ticket assigned to a technician
    - **In Progress** - Technician is actively working on the issue
    - **Resolved** - Issue has been fixed
    - **Closed** - Ticket completed and verified
    
    ## Contact Information
    
    **IT Support Team**
    - 📞 Phone: 9723100860
    - ✉️ Email: inquire@64-squares.com
    - 🕒 Hours: Monday - Friday, 9:00 AM - 6:00 PM
    
    ## Frequently Asked Questions
    
    **Q: How long does it take to resolve a ticket?**
    A: Resolution time depends on priority and complexity. Critical issues are addressed immediately, while low priority items may take 1-3 business days.
    
    **Q: Can I update my ticket after submission?**
    A: Currently, ticket updates must be requested through the support team. Contact us with your ticket number.
    
    **Q: How do I check my ticket status?**
    A: Use the "📋 My Tickets" page to view all your submitted tickets and their current status.
    """)
