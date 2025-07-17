"""
Ticket handling utilities for TeamLogic-AutoTask.
Contains ticket filtering, searching, and CRUD operations.
"""

import json
import os
from datetime import datetime, timedelta, date
from typing import List, Dict, Optional
from collections import Counter

import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from config import *


class TicketHandlers:
    """Handles ticket filtering, searching, and operations."""
    
    @staticmethod
    def load_kb_data() -> List[Dict]:
        """Load knowledgebase data."""
        try:
            if os.path.exists(KNOWLEDGEBASE_FILE):
                with open(KNOWLEDGEBASE_FILE, 'r') as f:
                    return json.load(f)
            return []
        except Exception as e:
            print(f"Error loading knowledgebase: {e}")
            return []
    
    @staticmethod
    def filter_tickets_by_date_range(kb_data: List[Dict], start_date: date, end_date: date) -> List[Dict]:
        """Filter tickets by date range."""
        filtered = []
        for entry in kb_data:
            ticket = entry.get('new_ticket', {})
            try:
                ticket_date = datetime.strptime(ticket.get('date', ''), '%Y-%m-%d').date()
                if start_date <= ticket_date <= end_date:
                    filtered.append(ticket)
            except (ValueError, TypeError):
                continue
        return sorted(filtered, key=lambda x: x.get("date", "") + x.get("time", ""), reverse=True)
    
    @staticmethod
    def filter_tickets_by_specific_date(kb_data: List[Dict], selected_date: date) -> List[Dict]:
        """Filter tickets by specific date."""
        filtered = []
        for entry in kb_data:
            ticket = entry.get('new_ticket', {})
            try:
                created_time = datetime.fromisoformat(ticket.get('date', '') + 'T' + ticket.get('time', ''))
                if created_time.date() == selected_date:
                    filtered.append(ticket)
            except (ValueError, TypeError):
                continue
        return sorted(filtered, key=lambda x: x.get("date", "") + x.get("time", ""), reverse=True)
    
    @staticmethod
    def filter_tickets_by_status(kb_data: List[Dict], status: str) -> List[Dict]:
        """Filter tickets by status."""
        filtered = []
        for entry in kb_data:
            ticket = entry.get('new_ticket', {})
            assignment = ticket.get('assignment_result', {})
            ticket_status = assignment.get('status', 'Open')
            if ticket_status.lower() == status.lower():
                filtered.append(ticket)
        return filtered
    
    @staticmethod
    def filter_tickets_by_priority(kb_data: List[Dict], priority: str) -> List[Dict]:
        """Filter tickets by priority."""
        filtered = []
        for entry in kb_data:
            ticket = entry.get('new_ticket', {})
            classified_data = ticket.get('classified_data', {})
            ticket_priority = classified_data.get('PRIORITY', {}).get('Value', 'Medium')
            if ticket_priority.lower() == priority.lower():
                filtered.append(ticket)
        return filtered
    
    @staticmethod
    def filter_tickets_by_technician(kb_data: List[Dict], technician_email: str) -> List[Dict]:
        """Filter tickets by assigned technician."""
        filtered = []
        for entry in kb_data:
            ticket = entry.get('new_ticket', {})
            assignment = ticket.get('assignment_result', {})
            assigned_email = assignment.get('technician_email', '')
            if assigned_email.lower() == technician_email.lower():
                filtered.append(ticket)
        return filtered
    
    @staticmethod
    def search_tickets_by_number(kb_data: List[Dict], ticket_number: str) -> List[Dict]:
        """Search for tickets by ticket number or partial match."""
        if not ticket_number or not ticket_number.strip():
            return []
        
        search_term = ticket_number.strip().lower()
        results = []
        
        for entry in kb_data:
            ticket = entry.get('new_ticket', {})
            ticket_num = ticket.get('ticket_number', '').lower()
            if search_term in ticket_num:
                results.append(ticket)
        
        return sorted(results, key=lambda x: x.get("date", "") + x.get("time", ""), reverse=True)
    
    @staticmethod
    def search_tickets_by_content(kb_data: List[Dict], search_term: str) -> List[Dict]:
        """Search tickets by title and description content."""
        if not search_term or not search_term.strip():
            return []
        
        search_term = search_term.strip().lower()
        results = []
        
        for entry in kb_data:
            ticket = entry.get('new_ticket', {})
            title = ticket.get('title', '').lower()
            description = ticket.get('description', '').lower()
            
            if search_term in title or search_term in description:
                results.append(ticket)
        
        return sorted(results, key=lambda x: x.get("date", "") + x.get("time", ""), reverse=True)
    
    @staticmethod
    def get_ticket_statistics(kb_data: List[Dict]) -> Dict:
        """Get comprehensive ticket statistics."""
        tickets = [entry.get('new_ticket', {}) for entry in kb_data]
        
        # Status statistics
        status_counts = Counter()
        priority_counts = Counter()
        category_counts = Counter()
        technician_counts = Counter()
        
        for ticket in tickets:
            # Status
            assignment = ticket.get('assignment_result', {})
            status = assignment.get('status', 'Open')
            status_counts[status] += 1
            
            # Priority
            classified_data = ticket.get('classified_data', {})
            priority = classified_data.get('PRIORITY', {}).get('Value', 'Medium')
            priority_counts[priority] += 1
            
            # Category
            category = classified_data.get('TICKETCATEGORY', {}).get('Value', 'General')
            category_counts[category] += 1
            
            # Technician
            tech_email = assignment.get('technician_email', 'Unassigned')
            technician_counts[tech_email] += 1
        
        # Time-based statistics
        today = datetime.now().date()
        yesterday = today - timedelta(days=1)
        this_week = today - timedelta(days=7)
        
        today_count = 0
        yesterday_count = 0
        week_count = 0
        
        for ticket in tickets:
            try:
                ticket_date = datetime.strptime(ticket.get('date', ''), '%Y-%m-%d').date()
                if ticket_date == today:
                    today_count += 1
                elif ticket_date == yesterday:
                    yesterday_count += 1
                elif ticket_date >= this_week:
                    week_count += 1
            except (ValueError, TypeError):
                continue
        
        return {
            'total_tickets': len(tickets),
            'status_distribution': dict(status_counts),
            'priority_distribution': dict(priority_counts),
            'category_distribution': dict(category_counts),
            'technician_workload': dict(technician_counts),
            'time_statistics': {
                'today': today_count,
                'yesterday': yesterday_count,
                'this_week': week_count
            }
        }
    
    @staticmethod
    def get_urgent_tickets(kb_data: List[Dict]) -> List[Dict]:
        """Get tickets marked as urgent or high priority."""
        urgent_tickets = []
        
        for entry in kb_data:
            ticket = entry.get('new_ticket', {})
            classified_data = ticket.get('classified_data', {})
            priority = classified_data.get('PRIORITY', {}).get('Value', 'Medium')
            
            if priority.lower() in ['critical', 'high', 'urgent']:
                urgent_tickets.append(ticket)
        
        return sorted(urgent_tickets, key=lambda x: x.get("date", "") + x.get("time", ""), reverse=True)
    
    @staticmethod
    def get_unassigned_tickets(kb_data: List[Dict]) -> List[Dict]:
        """Get tickets that haven't been assigned to a technician."""
        unassigned = []
        
        for entry in kb_data:
            ticket = entry.get('new_ticket', {})
            assignment = ticket.get('assignment_result', {})
            tech_email = assignment.get('technician_email', '')
            
            if not tech_email or tech_email.strip() == '':
                unassigned.append(ticket)
        
        return sorted(unassigned, key=lambda x: x.get("date", "") + x.get("time", ""), reverse=True)
    
    @staticmethod
    def get_recent_tickets(kb_data: List[Dict], hours: int = 24) -> List[Dict]:
        """Get tickets created within the specified number of hours."""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        recent = []
        
        for entry in kb_data:
            ticket = entry.get('new_ticket', {})
            try:
                created_time = datetime.fromisoformat(ticket.get('date', '') + 'T' + ticket.get('time', ''))
                if created_time >= cutoff_time:
                    recent.append(ticket)
            except (ValueError, TypeError):
                continue
        
        return sorted(recent, key=lambda x: x.get("date", "") + x.get("time", ""), reverse=True)
