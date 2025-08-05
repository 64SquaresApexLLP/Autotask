"""
Page controllers for TeamLogic-AutoTask.
Handles page routing and navigation logic.
"""

import streamlit as st
from typing import Dict, Any

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

# Import configuration constants
from config import PAGE_TITLE, PRIORITY_OPTIONS

# Import TicketHandlers for data operations
from src.core.ticket_handlers import TicketHandlers


class PageControllers:
    """Handles page routing and navigation for the application."""
    
    @staticmethod
    def show_user_dashboard(agent, data_manager, ticket_db):
        """Show user dashboard with user-specific navigation and functionality."""
        from ..ui.user_dashboard import (
            user_my_tickets_page,
            user_ticket_status_page,
            user_help_page
        )
        
        # Create user-specific sidebar
        PageControllers.create_user_sidebar(data_manager)
        
        # Show page based on navigation
        current_page = st.session_state.get('page', 'main')
        if current_page == "main":
            PageControllers.main_page(agent, data_manager, ticket_db)
        elif current_page == "user_my_tickets":
            user_my_tickets_page()
        elif current_page == "user_ticket_status":
            user_ticket_status_page()
        elif current_page == "user_help":
            user_help_page()
        else:
            # Default to main page for invalid pages
            st.session_state.page = "main"
            PageControllers.main_page(agent, data_manager, ticket_db)
    
    @staticmethod
    def show_technician_dashboard(agent, data_manager, ticket_db):
        """Show technician dashboard with technician-specific navigation and functionality."""
        from ..ui.technician_dashboard import (
            technician_dashboard_page,
            technician_my_tickets_page,
            technician_urgent_tickets_page,
            technician_analytics_page
        )
        
        # Create technician-specific sidebar
        PageControllers.create_technician_sidebar(data_manager)
        
        # Show page based on navigation
        current_page = st.session_state.get('page', 'technician_dashboard')
        if current_page == "technician_dashboard":
            technician_dashboard_page()
        elif current_page == "technician_my_tickets":
            technician_my_tickets_page()
        elif current_page == "technician_urgent_tickets":
            technician_urgent_tickets_page()
        elif current_page == "technician_analytics":
            technician_analytics_page()
        elif current_page == "technician_all_tickets":
            PageControllers.technician_dashboard_all_tickets_page(ticket_db)
        else:
            # Default to technician dashboard for invalid pages
            st.session_state.page = "technician_dashboard"
            technician_dashboard_page()
    
    @staticmethod
    def create_user_sidebar(data_manager):
        """Create sidebar for regular users."""
        import json
        import os
        
        with st.sidebar:
            # User info and logout
            user_info = st.session_state.get('user', {})
            st.markdown(f"### Welcome, {user_info.get('name', 'User')}!")
            st.caption(f"User ID: {user_info.get('id', 'N/A')}")
            
            if st.button("🚪 Logout", key="user_logout"):
                for key in ['user', 'technician', 'role', 'page']:
                    if key in st.session_state:
                        del st.session_state[key]
                st.rerun()
            
            st.markdown("---")
            st.markdown("## Navigation")
            
            # User Dashboard navigation
            user_pages = {
                "🏠 Home": "main",
                "📋 My Tickets": "user_my_tickets",
                "📊 Ticket Status": "user_ticket_status",
                "❓ Help": "user_help"
            }
            
            current_page = st.session_state.get('page', 'main')
            
            for label, page_key in user_pages.items():
                if st.button(label, key=f"nav_{page_key}", use_container_width=True):
                    st.session_state.page = page_key
                    st.rerun()
            
            st.markdown(f"""
            <div style="margin: 20px 0; padding: 10px; background-color: var(--accent); border-radius: 6px;">
            <small>Current page:</small><br>
            <strong>{current_page.replace('_', ' ').title()}</strong>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown("---")
            st.markdown("### Quick Stats")
            try:
                from config import KNOWLEDGEBASE_FILE
                if os.path.exists(KNOWLEDGEBASE_FILE):
                    with open(KNOWLEDGEBASE_FILE, 'r') as f:
                        kb_data = json.load(f)
                    total_tickets = len(kb_data)
                else:
                    total_tickets = 0
            except:
                total_tickets = 0
            st.metric("Total Tickets", total_tickets)
            
            st.markdown("---")
            st.markdown("""
            <div style="padding: 10px;">
            <h4>Need Help?</h4>
            <p>Contact IT Support:</p>
            <p>📞 9723100860<br>
            ✉️ inquire@64-squares.com</p>
            </div>
            """, unsafe_allow_html=True)
    
    @staticmethod
    def create_technician_sidebar(data_manager):
        """Create sidebar for technicians."""
        import json
        import os
        
        with st.sidebar:
            # Technician info and logout
            tech_info = st.session_state.get('technician', {})
            st.markdown(f"### Welcome, {tech_info.get('name', 'Technician')}!")
            st.caption(f"Tech ID: {tech_info.get('id', 'N/A')}")
            
            if st.button("🚪 Logout", key="tech_logout"):
                for key in ['user', 'technician', 'role', 'page']:
                    if key in st.session_state:
                        del st.session_state[key]
                st.rerun()
            
            st.markdown("---")
            st.markdown("## Navigation")
            
            # Technician Dashboard navigation
            technician_pages = {
                "🔧 Dashboard": "technician_dashboard",
                "📋 My Tickets": "technician_my_tickets",
                "🚨 Urgent Tickets": "technician_urgent_tickets",
                "📊 Analytics": "technician_analytics",
                "📋 All Tickets": "technician_all_tickets"
            }
            
            current_page = st.session_state.get('page', 'technician_dashboard')
            
            for label, page_key in technician_pages.items():
                if st.button(label, key=f"nav_{page_key}", use_container_width=True):
                    st.session_state.page = page_key
                    st.rerun()
            
            st.markdown(f"""
            <div style="margin: 20px 0; padding: 10px; background-color: var(--accent); border-radius: 6px;">
            <small>Current page:</small><br>
            <strong>{current_page.replace('_', ' ').title()}</strong>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown("---")
            st.markdown("### Quick Actions")
            if st.button("🔄 Refresh Data", key="tech_refresh"):
                st.rerun()
            
            st.markdown("---")
            st.markdown("### Today's Performance")
            # Get technician's tickets for metrics
            try:
                from config import KNOWLEDGEBASE_FILE
                if os.path.exists(KNOWLEDGEBASE_FILE):
                    with open(KNOWLEDGEBASE_FILE, 'r') as f:
                        kb_data = json.load(f)
                    tech_email = f"{tech_info.get('name', '').lower()}@company.com"
                    my_tickets = [entry['new_ticket'] for entry in kb_data
                                if entry['new_ticket'].get('assignment_result', {}).get('technician_email') == tech_email]
                    assigned_count = sum(1 for t in my_tickets if t.get('status', '').lower() in ['assigned', 'open'])
                    completed_count = sum(1 for t in my_tickets if t.get('status', '').lower() in ['resolved', 'closed'])
                    in_progress_count = sum(1 for t in my_tickets if t.get('status', '').lower() == 'in progress')
                    completion_rate = int((completed_count / len(my_tickets)) * 100) if my_tickets else 0
                else:
                    assigned_count = completed_count = in_progress_count = completion_rate = 0
            except:
                assigned_count = completed_count = in_progress_count = completion_rate = 0
                
            st.metric("Assigned", assigned_count)
            st.metric("In Progress", in_progress_count)
            st.metric("Completed", completed_count)
            st.metric("Completion Rate", f"{completion_rate}%")
    
    @staticmethod
    def main_page(agent, data_manager, ticket_db):
        """Main ticket submission page."""
        import pandas as pd
        from datetime import datetime, timedelta, date
        import re

        # Import required functions from main app
        from app import (
            validate_email, start_automatic_email_processing,
            stop_automatic_email_processing, fetch_and_process_emails,
            EMAIL_PROCESSING_STATUS
        )

        st.title(PAGE_TITLE)
        st.markdown("""
        <div class="card" style="background-color: var(--accent);">
        Submit a new support ticket and let our AI agent automatically classify it for faster resolution.
        </div>
        """, unsafe_allow_html=True)

        # --- Quick Stats using cached knowledgebase ---
        kb_data = TicketHandlers.load_kb_data()
        total_tickets = len(kb_data)
        st.markdown(f"**Total Tickets:** {total_tickets}")
        # Optionally, show a preview of the most recent ticket
        if kb_data:
            last_ticket = kb_data[-1]['new_ticket']
            st.markdown(f"**Most Recent Ticket:** {last_ticket.get('title', 'N/A')} ({last_ticket.get('date', 'N/A')} {last_ticket.get('time', 'N/A')})")

        # Ticket submission form
        with st.form("ticket_form"):
            st.markdown("### 📝 Ticket Details")

            col1, col2 = st.columns(2)
            with col1:
                ticket_name = st.text_input("👤 Your Name*", placeholder="Enter your full name")
                ticket_title = st.text_input("📋 Ticket Title*", placeholder="Brief summary of the issue")
                user_id = st.text_input("🆔 User ID*", placeholder="e.g., U001, EMP123", help="Your unique user identifier")

            with col2:
                user_email = st.text_input("📧 Email*", placeholder="your.email@company.com")
                phone_number = st.text_input("📞 Phone Number*", placeholder="e.g., +1234567890")
                due_date = st.date_input("📅 Due Date", value=date.today() + timedelta(days=1))

            ticket_description = st.text_area(
                "📄 Issue Description",
                placeholder="Describe your issue in detail...",
                height=150
            )

            initial_priority = st.selectbox(
                "⚡ Initial Priority",
                PRIORITY_OPTIONS,
                index=1
            )

            submitted = st.form_submit_button("🚀 Submit Ticket", type="primary")

            if submitted:
                # Validate required fields
                required_fields = {
                    "Name": ticket_name,
                    "Title": ticket_title,
                    "Description": ticket_description,
                    "User ID": user_id,
                    "Email": user_email,
                    "Phone Number": phone_number
                }
                missing_fields = [field for field, value in required_fields.items() if not value or not value.strip()]

                # Validate email format
                email_valid = validate_email(user_email) if user_email and user_email.strip() else False

                if missing_fields:
                    st.warning(f"⚠️ Please fill in all required fields: {', '.join(missing_fields)}")
                elif not email_valid:
                    st.error("⚠️ Please enter a valid email address.")
                else:
                    # Check if agent is properly initialized
                    if agent is None:
                        st.error("❌ Database connection failed. Cannot generate proper resolutions without historical data.")
                        st.info("🔑 **Expired MFA Code** - Get a fresh 6-digit code from your authenticator app")
                        st.info("🌐 **Network Issues** - Check your internet connection")
                        st.info("🔐 **Invalid Credentials** - Verify username/password")
                        st.warning("⚠️ **Resolution generation requires database access to historical tickets.**")
                        st.info("💡 Please fix the connection issue and try again for proper resolution generation.")
                        return
                    else:
                        with st.spinner("🔍 Analyzing your ticket..."):
                            try:
                                processed_ticket = agent.process_new_ticket(
                                    ticket_name=ticket_name,
                                    ticket_description=ticket_description,
                                    ticket_title=ticket_title,
                                    due_date=due_date.strftime("%Y-%m-%d"),
                                    priority_initial=initial_priority,
                                    user_email=user_email.strip(),
                                    user_id=user_id.strip(),
                                    phone_number=phone_number.strip()
                                )

                                if processed_ticket:
                                    ticket_number = processed_ticket.get('ticket_number', 'N/A')
                                    # Note: Database insertion is handled by the main /tickets endpoint
                                    # This prevents duplicate ticket creation
                                    st.success(f"✅ Ticket #{ticket_number} processed, classified, and resolution generated successfully!")
                                    if user_email and user_email.strip():
                                        st.info(f"📧 A confirmation email with resolution steps has been sent to {user_email}")

                                    PageControllers._display_ticket_results(processed_ticket)
                                else:
                                    st.error("Failed to process the ticket. Please check the logs for details.")
                            except Exception as e:
                                st.error(f"An unexpected error occurred: {e}")

        # About section
        PageControllers._display_about_section()

        # Email processing section
        PageControllers._display_email_processing_section(agent)
    
    @staticmethod
    def technician_dashboard_all_tickets_page(ticket_db):
        """Show all tickets from the database for the technician dashboard."""
        st.title("Technician Dashboard - All Tickets")
        all_tickets = []
        try:
            query = 'SELECT * FROM TEST_DB.PUBLIC.TICKETS'
            all_tickets = ticket_db.conn.execute_query(query)
        except Exception as e:
            st.error(f"Error fetching tickets: {e}")
            return
        
        if not all_tickets:
            st.info("No tickets found in the database.")
            return
        
        st.write(f"Found {len(all_tickets)} tickets in the database:")
        
        # Display tickets in a table
        import pandas as pd
        df = pd.DataFrame(all_tickets)
        st.dataframe(df, use_container_width=True)

    @staticmethod
    def _display_ticket_results(processed_ticket):
        """Display ticket processing results."""
        import pandas as pd

        classified_data = processed_ticket.get('classified_data', {})
        extracted_metadata = processed_ticket.get('extracted_metadata', {})
        resolution_note = processed_ticket.get('resolution_note', 'No resolution note generated')
        ticket_number = processed_ticket.get('ticket_number', 'N/A')

        # Display ticket summary
        with st.expander("📋 Classified Ticket Summary", expanded=True):
            cols = st.columns(4)
            cols[0].metric("Ticket Number", f"#{ticket_number}")
            cols[1].metric("Issue Type", classified_data.get('ISSUETYPE', {}).get('Label', 'N/A'))
            cols[2].metric("Type", classified_data.get('TICKETTYPE', {}).get('Label', 'N/A'))
            cols[3].metric("Priority", classified_data.get('PRIORITY', {}).get('Label', 'N/A'))

            st.markdown(f"""
            <div class="card">
            <table style="width:100%">
                <tr><td><strong>Ticket Title</strong></td><td>{processed_ticket.get('title', 'N/A')}</td></tr>
                <tr><td><strong>Main Issue</strong></td><td>{extracted_metadata.get('main_issue', 'N/A')}</td></tr>
                <tr><td><strong>Affected System</strong></td><td>{extracted_metadata.get('affected_system', 'N/A')}</td></tr>
                <tr><td><strong>Urgency Level</strong></td><td>{extracted_metadata.get('urgency_level', 'N/A')}</td></tr>
                <tr><td><strong>Error Messages</strong></td><td>{extracted_metadata.get('error_messages', 'N/A')}</td></tr>
            </table>
            </div>
            """, unsafe_allow_html=True)

        # Display full classification details
        with st.expander("📊 Full Classification Details", expanded=False):
            st.markdown("""
            <div class="card">
            <h4>Ticket Classification Details</h4>
            """, unsafe_allow_html=True)

            # Tabular display for classification fields
            class_fields = [
                ("ISSUETYPE", "Issue Type"),
                ("SUBISSUETYPE", "Sub-Issue Type"),
                ("TICKETCATEGORY", "Ticket Category"),
                ("TICKETTYPE", "Ticket Type"),
                ("STATUS", "Status"),
                ("PRIORITY", "Priority")
            ]
            table_data = []
            for field, label in class_fields:
                val = classified_data.get(field, {})
                table_data.append({
                    "Field": label,
                    "Label": val.get('Label', 'N/A')
                })
            df = pd.DataFrame(table_data)
            st.table(df)
            st.markdown(f"**Ticket Title:** {processed_ticket.get('title', 'N/A')}")
            st.markdown(f"**Description:** {processed_ticket.get('description', 'N/A')}")
            st.markdown("</div>", unsafe_allow_html=True)

        # Display Resolution Note
        with st.expander("🔧 Generated Resolution Note", expanded=True):
            processed_note = resolution_note.replace('**', '<strong>').replace('</strong>', '</strong>').replace('\n', '<br>')
            st.markdown(f"""
            <div class="card" style="background-color: #1e4620; border-left: 4px solid #28a745;">
            <h4 style="color: #d4edda; margin-bottom: 15px;">💡 Recommended Resolution</h4>
            <div style="color: #d4edda; line-height: 1.6;">
            {processed_note}
            </div>
            </div>
            """, unsafe_allow_html=True)

        # Assignment information
        assignment_result = processed_ticket.get('assignment_result', {})
        assigned_technician = assignment_result.get('assigned_technician', 'IT Manager')
        technician_email = assignment_result.get('technician_email', 'itmanager@company.com')

        # Next steps
        st.markdown(f"""
        <div class="card" style="background-color: var(--accent);">
        <h4>Next Steps</h4>
        <ol>
            <li>Your ticket <b>#{ticket_number}</b> has been assigned to <b>{assigned_technician}</b> from the <b>{classified_data.get('ISSUETYPE', {}).get('Label', 'N/A')}</b> team</li>
            <li>Assigned technician contact: <b>{technician_email}</b></li>
            <li>A resolution note has been automatically generated based on similar historical tickets</li>
            <li>The assigned technician will contact you within 2 business hours</li>
            <li>Priority level: <b>{classified_data.get('PRIORITY', {}).get('Label', 'N/A')}</b> - Response time varies accordingly</li>
            <li>Try the suggested resolution steps above before escalating</li>
            <li>Reference your ticket using number <b>#{ticket_number}</b> for all future communications</li>
        </ol>
        </div>
        """, unsafe_allow_html=True)

    @staticmethod
    def _display_about_section():
        """Display the about section."""
        st.markdown("---")
        st.markdown("""
        <div class="card">
        <h3>About This System</h3>
        <p>This AI-powered intake, classification, assignment, and resolution system automatically:</p>
        <ul>
            <li>Extracts metadata from new tickets using AI</li>
            <li>Classifies tickets into predefined categories</li>
            <li>Assigns tickets to the most suitable technician based on skills and workload</li>
            <li>Generates resolution notes based on similar historical tickets</li>
            <li>Routes tickets to the appropriate support teams</li>
            <li>Provides confidence-based resolution suggestions</li>
            <li>Stores all data for continuous improvement</li>
        </ul>
        <p><strong>Workflow:</strong> Intake → Classification → Assignment → Resolution Generation</p>
        </div>
        """, unsafe_allow_html=True)

    @staticmethod
    def _display_email_processing_section(agent):
        """Display the email processing section."""
        # Use the integrated email processing methods from the intake agent
        start_automatic_email_processing = agent.start_automatic_email_processing
        stop_automatic_email_processing = agent.stop_automatic_email_processing
        fetch_and_process_emails = agent.process_recent_emails
        EMAIL_PROCESSING_STATUS = agent.get_email_processing_status()

        with st.expander("📧 Email Processing with Image Analysis", expanded=False):
            st.markdown("""
            **Enhanced Email Processing Features:**
            - 📎 **Image Attachment Processing**: Automatically extracts text and metadata from screenshots
            - 🔍 **Error Detection**: Identifies error dialogs and technical issues in images
            - 🏷️ **Smart Classification**: Uses image content for better ticket categorization
            - ⚡ **Priority Assignment**: Higher priority for tickets with error screenshots
            - ⚡ **Real-Time Processing**: Only processes emails from last 5 minutes
            - 🎯 **Intelligent Filtering**: Skips newsletters, promotions, and non-support emails
            """)

            # Automatic Email Processing Section
            st.markdown("### 🔄 Automatic Email Processing")
            
            # Show automatic status
            if EMAIL_PROCESSING_STATUS["is_running"]:
                st.success("✅ **Automatic email processing is ACTIVE** - Checking for new emails every 5 minutes")
            else:
                st.warning("⚠️ **Automatic email processing is INACTIVE**")

            col1, col2, col3 = st.columns([2, 2, 2])

            with col1:
                if EMAIL_PROCESSING_STATUS["is_running"]:
                    st.info("🟢 Auto processing is running")
                else:
                    if st.button("🚀 Start Auto Processing", type="primary"):
                        with st.spinner("Starting automatic email processing..."):
                            result = start_automatic_email_processing()
                            if "✅" in result:
                                st.success(result)
                                st.rerun()
                            else:
                                st.error(result)

            with col2:
                if EMAIL_PROCESSING_STATUS["is_running"]:
                    if st.button("🛑 Stop Auto Processing"):
                        result = stop_automatic_email_processing()
                        if "✅" in result:
                            st.success(result)
                            st.rerun()
                        else:
                            st.warning(result)
                else:
                    st.info("Auto processing stopped")

            with col3:
                if st.button("🔄 Refresh Status"):
                    st.rerun()

            # Status Display
            st.markdown("### 📊 Auto Processing Status")
            status_col1, status_col2, status_col3, status_col4 = st.columns(4)

            with status_col1:
                status_icon = "🟢" if EMAIL_PROCESSING_STATUS["is_running"] else "🔴"
                st.metric("Status", f"{status_icon} {'Running' if EMAIL_PROCESSING_STATUS['is_running'] else 'Stopped'}")

            with status_col2:
                st.metric("Total Processed", EMAIL_PROCESSING_STATUS["total_processed"])

            with status_col3:
                st.metric("Errors", EMAIL_PROCESSING_STATUS["error_count"])

            with status_col4:
                last_processed = EMAIL_PROCESSING_STATUS["last_processed"] or "Never"
                if last_processed != "Never":
                    last_processed = last_processed.split(" ")[1]  # Show only time
                st.metric("Last Processed", last_processed)

            # Recent Activity Log
            if EMAIL_PROCESSING_STATUS["recent_logs"]:
                st.markdown("### 📝 Recent Activity")
                for log in EMAIL_PROCESSING_STATUS["recent_logs"][-5:]:  # Show last 5 logs
                    level_icon = {"INFO": "ℹ️", "SUCCESS": "✅", "ERROR": "❌"}.get(log["level"], "📝")
                    st.text(f"{level_icon} [{log['timestamp'].split(' ')[1]}] {log['message']}")

            # Recently Auto-Processed Emails
            if 'auto_processed_emails' in st.session_state and st.session_state.auto_processed_emails:
                st.markdown("### 📧 Recently Auto-Processed Emails")
                recent_emails = st.session_state.auto_processed_emails[-10:]  # Show last 10

                for i, email_info in enumerate(recent_emails):
                    with st.container():
                        col1, col2, col3 = st.columns([3, 2, 1])
                        with col1:
                            st.write(f"**{email_info.get('subject', 'No subject')}**")
                            st.write(f"From: {email_info.get('from', 'Unknown')}")
                            if email_info.get('ticket_number'):
                                st.write(f"🎫 Ticket: #{email_info.get('ticket_number')}")
                        with col2:
                            st.write(f"Due: {email_info.get('due_date', 'N/A')}")
                            if email_info.get('has_images'):
                                st.write(f"🖼️ {email_info.get('image_count', 0)} images")
                        with col3:
                            if email_info.get('has_images'):
                                st.success("📎 Images")
                            else:
                                st.info("📝 Text")

            st.markdown("---")

            # Manual Processing Section
            st.markdown("### 🔧 Manual Email Processing")
            if st.button("📧 Process Emails Now (Manual)", type="secondary"):
                with st.spinner("Checking support inbox and processing emails with image analysis..."):
                    results = fetch_and_process_emails(agent)
                    if isinstance(results, str):
                        st.error(results)
                    elif results:
                        st.success(f"✅ Processed {len(results)} new email(s) into tickets.")

                        # Show detailed results
                        for r in results:
                            col1, col2, col3 = st.columns([3, 2, 1])
                            with col1:
                                st.write(f"**{r['subject']}**")
                                st.write(f"From: {r['from']}")
                                if r.get('ticket_number'):
                                    st.write(f"🎫 Ticket: #{r.get('ticket_number')}")
                            with col2:
                                st.write(f"Due: {r['due_date']}")
                                if r.get('has_images'):
                                    st.write(f"🖼️ {r.get('image_count', 0)} images processed")
                            with col3:
                                if r.get('has_images'):
                                    st.success("📎 Images")
                                else:
                                    st.info("📝 Text only")
                    else:
                        st.info("No new support emails found.")
