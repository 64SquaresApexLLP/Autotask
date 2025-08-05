#!/usr/bin/env python3
"""
Test Workload Transfer Functionality
Test that when tickets are reassigned, workload is properly transferred between technicians
"""

import sys
import os
import requests
import json

# Add the src directory to the path
sys.path.append('src')

def test_workload_transfer():
    """Test workload transfer when reassigning tickets"""
    print("🧪 TESTING WORKLOAD TRANSFER FUNCTIONALITY")
    print("=" * 60)
    
    # Test data
    test_ticket_number = "T20250804.0001"  # Use a test ticket number
    
    try:
        # Step 1: Check initial workload for technicians
        print("📊 Step 1: Checking initial technician workloads...")
        
        response = requests.get("http://localhost:8001/technicians")
        if response.status_code == 200:
            technicians = response.json()
            print(f"✅ Retrieved {len(technicians)} technicians")
            
            # Find T001 and another technician
            t001 = None
            other_tech = None
            
            for tech in technicians:
                if tech.get('id') == 'T001':
                    t001 = tech
                elif tech.get('id') in ['T103', 'T104', 'T106']:
                    other_tech = tech
                    
            if t001 and other_tech:
                print(f"📋 T001 initial workload: {t001.get('current_workload', 0)}")
                print(f"📋 {other_tech.get('id')} initial workload: {other_tech.get('current_workload', 0)}")
            else:
                print("❌ Could not find required technicians")
                return False
        else:
            print(f"❌ Failed to get technicians: {response.status_code}")
            return False
        
        # Step 2: Assign ticket to T001 first
        print(f"\n📋 Step 2: Assigning ticket {test_ticket_number} to T001...")
        
        response = requests.post(
            f"http://localhost:8001/tickets/{test_ticket_number}/assign",
            json={"technician_id": "T001"},
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Ticket assigned to T001: {result.get('message')}")
        else:
            print(f"❌ Failed to assign ticket to T001: {response.status_code}")
            print(f"📧 Response: {response.text}")
            return False
        
        # Step 3: Check workload after first assignment
        print(f"\n📊 Step 3: Checking workload after T001 assignment...")
        
        response = requests.get("http://localhost:8001/technicians")
        if response.status_code == 200:
            technicians = response.json()
            
            for tech in technicians:
                if tech.get('id') == 'T001':
                    t001_after = tech
                    print(f"📋 T001 workload after assignment: {t001_after.get('current_workload', 0)}")
                    break
        else:
            print(f"❌ Failed to get technicians after assignment: {response.status_code}")
            return False
        
        # Step 4: Reassign ticket to another technician
        print(f"\n🔄 Step 4: Reassigning ticket {test_ticket_number} to {other_tech.get('id')}...")
        
        response = requests.post(
            f"http://localhost:8001/tickets/{test_ticket_number}/assign",
            json={"technician_id": other_tech.get('id')},
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Ticket reassigned: {result.get('message')}")
            print(f"📋 Previous technician: {result.get('previous_technician')}")
            print(f"📋 New technician: {result.get('new_technician')}")
            print(f"📋 Workload transferred: {result.get('workload_transferred')}")
        else:
            print(f"❌ Failed to reassign ticket: {response.status_code}")
            print(f"📧 Response: {response.text}")
            return False
        
        # Step 5: Check final workload
        print(f"\n📊 Step 5: Checking final workload after reassignment...")
        
        response = requests.get("http://localhost:8001/technicians")
        if response.status_code == 200:
            technicians = response.json()
            
            t001_final = None
            other_tech_final = None
            
            for tech in technicians:
                if tech.get('id') == 'T001':
                    t001_final = tech
                elif tech.get('id') == other_tech.get('id'):
                    other_tech_final = tech
            
            if t001_final and other_tech_final:
                print(f"📋 T001 final workload: {t001_final.get('current_workload', 0)}")
                print(f"📋 {other_tech_final.get('id')} final workload: {other_tech_final.get('current_workload', 0)}")
                
                # Verify workload transfer
                t001_initial = int(t001.get('current_workload', 0))
                t001_after_assignment = int(t001_after.get('current_workload', 0))
                t001_final_workload = int(t001_final.get('current_workload', 0))
                
                other_initial = int(other_tech.get('current_workload', 0))
                other_final_workload = int(other_tech_final.get('current_workload', 0))
                
                print(f"\n📊 WORKLOAD TRANSFER VERIFICATION:")
                print(f"T001: {t001_initial} → {t001_after_assignment} → {t001_final_workload}")
                print(f"{other_tech.get('id')}: {other_initial} → {other_final_workload}")
                
                # Check if workload was properly transferred
                if (t001_after_assignment == t001_initial + 1 and 
                    t001_final_workload == t001_initial and
                    other_final_workload == other_initial + 1):
                    print("✅ WORKLOAD TRANSFER SUCCESSFUL!")
                    print("✅ T001 workload: +1 then -1 (back to original)")
                    print(f"✅ {other_tech.get('id')} workload: +1 (ticket assigned)")
                    return True
                else:
                    print("❌ WORKLOAD TRANSFER FAILED!")
                    print("❌ Workload changes don't match expected pattern")
                    return False
            else:
                print("❌ Could not find technicians for final check")
                return False
        else:
            print(f"❌ Failed to get final technician data: {response.status_code}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to backend server")
        print("💡 Make sure the backend is running on http://localhost:8001")
        return False
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        return False

def test_database_consistency():
    """Test that database workload matches actual ticket assignments"""
    print("\n🗄️ TESTING DATABASE CONSISTENCY")
    print("=" * 60)
    
    try:
        # Get all tickets
        print("📋 Getting all tickets...")
        response = requests.get("http://localhost:8001/tickets?limit=100")
        if response.status_code == 200:
            tickets = response.json()
            print(f"✅ Retrieved {len(tickets)} tickets")
            
            # Count tickets per technician (only active tickets that contribute to workload)
            technician_ticket_counts = {}
            for ticket in tickets:
                # Try different possible field names for technician ID
                tech_id = ticket.get('TECHNICIAN_ID') or ticket.get('technician_id') or ticket.get('assigned_technician')
                status = ticket.get('STATUS') or ticket.get('status', 'Unknown')
                
                # Only count tickets that are not closed/resolved (active tickets)
                if tech_id and status.lower() not in ['closed', 'resolved']:
                    technician_ticket_counts[tech_id] = technician_ticket_counts.get(tech_id, 0) + 1
            
            print(f"📊 Ticket counts by technician: {technician_ticket_counts}")
            
            # Also show ticket statuses for debugging
            print(f"📊 Ticket statuses:")
            status_counts = {}
            for ticket in tickets:
                status = ticket.get('STATUS') or ticket.get('status', 'Unknown')
                status_counts[status] = status_counts.get(status, 0) + 1
            print(f"  {status_counts}")
            
            # Get technician workloads from database
            print("📋 Getting technician workloads from database...")
            response = requests.get("http://localhost:8001/technicians")
            if response.status_code == 200:
                technicians = response.json()
                
                print("📊 Comparing ticket counts vs database workload:")
                for tech in technicians:
                    tech_id = tech.get('id')
                    db_workload = int(tech.get('current_workload', 0))
                    actual_tickets = technician_ticket_counts.get(tech_id, 0)
                    
                    print(f"  {tech_id}: Database workload = {db_workload}, Actual tickets = {actual_tickets}")
                    
                    if db_workload != actual_tickets:
                        print(f"  ⚠️  MISMATCH for {tech_id}!")
                        return False
                    else:
                        print(f"  ✅ Match for {tech_id}")
                
                print("✅ All technician workloads match actual ticket assignments!")
                return True
            else:
                print(f"❌ Failed to get technicians: {response.status_code}")
                return False
        else:
            print(f"❌ Failed to get tickets: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Database consistency test failed: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Starting workload transfer tests...")
    
    # Test workload transfer
    transfer_test = test_workload_transfer()
    
    # Test database consistency
    consistency_test = test_database_consistency()
    
    print("\n" + "=" * 60)
    print("📊 TEST RESULTS SUMMARY")
    print("=" * 60)
    print(f"🔄 Workload Transfer: {'✅ PASSED' if transfer_test else '❌ FAILED'}")
    print(f"🗄️ Database Consistency: {'✅ PASSED' if consistency_test else '❌ FAILED'}")
    
    if transfer_test and consistency_test:
        print("\n🎉 All tests PASSED! Workload transfer functionality is working correctly.")
        print("✅ When T001 assigns a ticket to another technician:")
        print("   - T001's workload decreases by 1")
        print("   - Assigned technician's workload increases by 1")
        print("   - Database workload matches actual ticket assignments")
    else:
        print("\n⚠️  Some tests FAILED. Please check the implementation.") 