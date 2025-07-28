# TeamLogic AutoTask Backend API Endpoints

## Health Check
- **GET /health**
  - Returns: `{ "status": "ok" }`

## Get All Tickets
- **GET /tickets**
  - Query Params:
    - `limit` (int, default 50, max 100)
    - `offset` (int, default 0)
    - `status` (optional)
    - `priority` (optional)
  - Returns: List of ticket objects from TEST_DB.PUBLIC.TICKETS

## Get Ticket by Number
- **GET /tickets/{ticket_number}**
  - Path Param: `ticket_number` (str)
  - Returns: Ticket object or 404 if not found

## Get Technician by Ticket Number
- **GET /tickets/{ticket_number}/technician**
  - Path Param: `ticket_number` (str)
  - Returns: Technician object (name, email) or 404 if not found

## Create Ticket
- **POST /tickets**
  - Body (JSON):
    - `title` (str, required)
    - `description` (str, required)
    - `due_date` (str, required)
    - `user_email` (str, optional)
    - `priority` (str, optional)
    - `requester_name` (str, optional)
  - Returns: `{ "ticket_number": ..., "status": "created" }`
  - Executes full agentic workflow and inserts ticket into TEST_DB.PUBLIC.TICKETS 