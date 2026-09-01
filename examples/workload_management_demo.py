#!/usr/bin/env python3
"""
Workload Management Demo

This script demonstrates the new dynamic workload management functionality
in the Assignment Agent.

Features demonstrated:
1. Dynamic workload increment when tickets are assigned
2. Workload consideration in technician selection
3. Workload refresh from active ticket counts
4. Workload decrement when tickets are completed

Author: AutoTask Integration System
Date: 2025-08-03
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from agents.assignment_agent import (
    AssignmentAgentIntegration, 
    assign_ticket,
    update_technician_workload_by_email,
    refresh_all_workloads
)

def demo_workload_management():
    """
    Demonstrate the workload management functionality
    """
    print("🔧 Dynamic Workload Management Demo")
    print("=" * 50)
    
    # Note: This demo shows the API usage - actual database connection required for execution
    print("📋 Available Workload Management Functions:")
    print()
    
    print("1. 📈 Increment Technician Workload:")
    print("   update_technician_workload_by_email('tech@company.com', 1, db_connection)")
    print("   → Increases workload by 1 when ticket is assigned")
    print()
    
    print("2. 📉 Decrement Technician Workload:")
    print("   update_technician_workload_by_email('tech@company.com', -1, db_connection)")
    print("   → Decreases workload by 1 when ticket is completed")
    print()
    
    print("3. 🔄 Refresh All Workloads:")
    print("   refresh_all_workloads(db_connection)")
    print("   → Counts active tickets and updates all technician workloads")
    print()
    
    print("4. 🎯 Assignment with Workload Consideration:")
    print("   assign_ticket(ticket_data, db_connection)")
    print("   → Automatically considers current workload in technician selection")
    print("   → Increments assigned technician's workload by +1")
    print()
    
    print("🔄 Assignment Process with Dynamic Workload:")
    print("1. Retrieve technicians with current workloads")
    print("2. Evaluate candidates based on skills, availability, and workload")
    print("3. Select best candidate (prioritizing lower workload within same tier)")
    print("4. Assign ticket to selected technician")
    print("5. Automatically increment technician's workload (+1)")
    print("6. Log workload change for monitoring")
    print()
    
    print("📊 Workload Prioritization Logic:")
    print("• Within same skill match tier, technicians with lower workload are preferred")
    print("• Sorting order: Priority Tier → Current Workload → Skill Match %")
    print("• Example: Tier 1 (5 tickets) beats Tier 1 (8 tickets)")
    print()
    
    print("⚡ Real-time Features:")
    print("• Workload automatically updated in database upon assignment")
    print("• Workload monitoring integration available")
    print("• Workload refresh can be triggered manually or scheduled")
    print("• Workload alerts for high/critical thresholds")
    print()
    
    # Example ticket data
    example_ticket = {
        'ticket_id': 'TKT-2024-DEMO',
        'issue': 'Email server performance issue',
        'description': 'Users experiencing slow email response times',
        'issue_type': 'Email',
        'sub_issue_type': 'Performance',
        'ticket_category': 'Infrastructure',
        'priority': 'High',
        'due_date': '2024-08-05T16:00:00Z',
        'user_name': 'Demo User',
        'user_email': 'demo@company.com'
    }
    
    print("📝 Example Ticket Assignment with Workload Management:")
    print(f"Ticket ID: {example_ticket['ticket_id']}")
    print(f"Issue: {example_ticket['issue']}")
    print(f"Priority: {example_ticket['priority']}")
    print()
    
    print("🎯 Expected Assignment Flow:")
    print("1. Load technicians: [Alice (2 tickets), Bob (5 tickets), Carol (3 tickets)]")
    print("2. Filter by availability and skills")
    print("3. Rank by: Tier → Workload → Skill Match")
    print("4. Select: Alice (lowest workload in tier)")
    print("5. Assign ticket to Alice")
    print("6. Update Alice's workload: 2 → 3 tickets")
    print("7. Return assignment result")
    print()
    
    print("✅ Dynamic workload management ensures:")
    print("• Fair distribution of tickets among technicians")
    print("• Prevention of technician overload")
    print("• Real-time workload tracking")
    print("• Optimal resource utilization")
    print()
    
    print("🔧 Integration Points:")
    print("• Webhook handlers can call workload update functions")
    print("• Ticket completion triggers workload decrement")
    print("• Monitoring systems can track workload changes")
    print("• Admin interfaces can refresh workloads manually")

def demo_workload_scenarios():
    """
    Demonstrate different workload management scenarios
    """
    print("\n" + "=" * 50)
    print("📊 Workload Management Scenarios")
    print("=" * 50)
    
    scenarios = [
        {
            "name": "Balanced Assignment",
            "technicians": [
                {"name": "Alice", "workload": 3, "skills": "Strong"},
                {"name": "Bob", "workload": 3, "skills": "Strong"},
                {"name": "Carol", "workload": 5, "skills": "Strong"}
            ],
            "selected": "Alice or Bob (random between equal workloads)",
            "reason": "Equal workload and skills - random selection"
        },
        {
            "name": "Workload-Based Selection",
            "technicians": [
                {"name": "Alice", "workload": 2, "skills": "Mid"},
                {"name": "Bob", "workload": 6, "skills": "Strong"},
                {"name": "Carol", "workload": 4, "skills": "Strong"}
            ],
            "selected": "Carol",
            "reason": "Strong skill match with lower workload than Bob"
        },
        {
            "name": "Skill vs Workload Trade-off",
            "technicians": [
                {"name": "Alice", "workload": 1, "skills": "Weak"},
                {"name": "Bob", "workload": 8, "skills": "Strong"},
                {"name": "Carol", "workload": 4, "skills": "Mid"}
            ],
            "selected": "Bob",
            "reason": "Strong skill match outweighs higher workload (Tier 1 vs Tier 2)"
        }
    ]
    
    for i, scenario in enumerate(scenarios, 1):
        print(f"\n{i}. {scenario['name']}:")
        print("   Technicians:")
        for tech in scenario['technicians']:
            print(f"   • {tech['name']}: {tech['workload']} tickets, {tech['skills']} match")
        print(f"   → Selected: {scenario['selected']}")
        print(f"   → Reason: {scenario['reason']}")

if __name__ == "__main__":
    demo_workload_management()
    demo_workload_scenarios()
    
    print("\n" + "=" * 50)
    print("🚀 Ready to implement dynamic workload management!")
    print("Connect to your Snowflake database and start using the enhanced assignment agent.")
    print("=" * 50)
