# Dynamic Workload Management Refactor

## Overview
The assignment agent has been refactored to include dynamic workload management functionality. When a ticket is assigned to a technician, the system now automatically increments their workload count and considers current workload in the assignment decision process.

## Key Changes Made

### 1. Enhanced Candidate Selection Logic
- **File**: `src/agents/assignment_agent.py`
- **Method**: `select_best_candidate()`
- **Changes**: 
  - Modified sorting logic to consider current workload as secondary criteria
  - Sorting order: Priority Tier → Current Workload (ascending) → Skill Match % (descending)
  - Technicians with lower workload are now preferred within the same skill tier

### 2. New Workload Management Methods

#### `update_technician_workload(technician_id, increment)`
- Updates technician workload in database by specified increment
- Supports both positive (assignment) and negative (completion) increments
- Returns boolean indicating success/failure

#### `refresh_all_technician_workloads()`
- Counts active tickets per technician from TICKETS table
- Updates CURRENT_WORKLOAD column in TECHNICIAN_DUMMY_DATA table
- Returns dictionary mapping technician email to current workload count
- Filters out closed/resolved/cancelled tickets

#### `get_technician_current_workload(technician_id)`
- Retrieves current workload for a specific technician
- Returns integer workload count

#### `handle_ticket_completion(ticket_id, technician_email)`
- Handles ticket completion by decrementing technician workload
- Ensures workload doesn't go below 0 using GREATEST() function
- Logs completion for audit trail

### 3. Public Interface Functions

#### `update_technician_workload_by_email(email, increment, db_connection)`
- Public function to update workload by technician email
- Can be called from webhook handlers or other system components

#### `refresh_all_workloads(db_connection)`
- Public function to refresh all technician workloads
- Useful for scheduled maintenance or manual refresh operations

### 4. Integrated Assignment Process
- **Method**: `process_ticket_assignment()`
- **Enhancement**: Automatically increments assigned technician's workload by +1
- **Logging**: Enhanced logging to show workload changes
- **Error Handling**: Graceful handling if workload update fails

### 5. Enhanced Reasoning and Logging
- Updated candidate evaluation reasoning to include workload information
- Improved selection logging to show workload considerations
- Added workload change notifications

## Database Schema Requirements

The system expects the following table structure:

```sql
-- TECHNICIAN_DUMMY_DATA table should have:
TECHNICIAN_ID (String) - Primary key
NAME (String) - Technician name
EMAIL (String) - Technician email
ROLE (String) - Technician role
SKILLS (String) - JSON array or comma-separated skills
CURRENT_WORKLOAD (Integer) - Current active ticket count
SPECIALIZATIONS (String) - JSON array or comma-separated specializations

-- TICKETS table should have:
TICKETNUMBER (String) - Ticket identifier
TECHNICIANEMAIL (String) - Assigned technician email
STATUS (String) - Ticket status (NULL, 'Closed', 'Resolved', 'Cancelled')
```

## Assignment Priority Logic

The enhanced assignment logic follows this hierarchy:

1. **Tier 1**: Available + Strong match (≥70%) + Lowest workload
2. **Tier 2**: Available + Mid match (60-69%) + Lowest workload  
3. **Tier 3**: Available + Weak match (<60%) + Lowest workload
4. **Tier 6**: Fallback assignment

Within each tier, technicians are sorted by:
1. Current workload (ascending - lower is better)
2. Skill match percentage (descending - higher is better)

## Usage Examples

### Basic Assignment with Workload Management
```python
from agents.assignment_agent import assign_ticket

# Assign ticket - workload automatically incremented
result = assign_ticket(ticket_data, db_connection)
```

### Manual Workload Updates
```python
from agents.assignment_agent import update_technician_workload_by_email

# Increment workload when ticket assigned externally
update_technician_workload_by_email('tech@company.com', 1, db_connection)

# Decrement workload when ticket completed
update_technician_workload_by_email('tech@company.com', -1, db_connection)
```

### Refresh All Workloads
```python
from agents.assignment_agent import refresh_all_workloads

# Refresh all technician workloads from active ticket counts
workload_summary = refresh_all_workloads(db_connection)
print(f"Updated workloads: {workload_summary}")
```

## Integration Points

### Webhook Handlers
- Call `update_technician_workload_by_email()` when tickets are completed
- Call `refresh_all_workloads()` for periodic synchronization

### Monitoring Systems
- Use workload data for capacity planning
- Set up alerts for high workload thresholds
- Track workload distribution metrics

### Admin Interfaces
- Provide manual workload refresh functionality
- Display real-time workload statistics
- Allow manual workload adjustments if needed

## Benefits

1. **Fair Distribution**: Ensures tickets are distributed evenly among technicians
2. **Prevent Overload**: Considers current workload to avoid overwhelming technicians
3. **Real-time Tracking**: Maintains accurate workload counts in real-time
4. **Optimal Resource Utilization**: Balances skill matching with workload distribution
5. **Audit Trail**: Logs all workload changes for monitoring and analysis

## Testing

A demonstration script is available at `examples/workload_management_demo.py` that shows:
- API usage examples
- Different assignment scenarios
- Expected behavior with various workload distributions

## Backward Compatibility

All existing functionality remains unchanged. The workload management features are additive and don't break existing integrations. The assignment logic enhancement only improves the selection process by considering workload as an additional factor.
