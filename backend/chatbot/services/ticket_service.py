"""Ticket management service."""

import logging
from datetime import datetime, timedelta
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_, or_
from ..database import Ticket, TechnicianDummyData
from ..models import TicketCreate, TicketUpdate, TicketResponse

logger = logging.getLogger(__name__)


class TicketService:
    """Service for ticket management operations."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_recent_assigned_tickets(
        self,
        technician_email: str,
        limit: int = 10,
        days_back: int = 30
    ) -> List[Ticket]:
        """Get recent tickets assigned to a technician by email."""
        tickets = self.db.query(Ticket).filter(
            Ticket.technicianemail == technician_email
        ).limit(limit).all()

        logger.info(f"Retrieved {len(tickets)} tickets for technician {technician_email}")
        return tickets
    
    def get_ticket_by_id(self, ticket_id: str) -> Optional[Ticket]:
        """Get detailed ticket information by ticket number (ID)."""
        ticket = self.db.query(Ticket).filter(Ticket.ticketnumber == ticket_id).first()
        if ticket:
            logger.info(f"Retrieved ticket {ticket_id}")
        else:
            logger.warning(f"Ticket {ticket_id} not found")
        return ticket

    def get_ticket_by_number(self, ticket_number: str) -> Optional[Ticket]:
        """Get ticket by ticket number."""
        ticket = self.db.query(Ticket).filter(Ticket.ticketnumber == ticket_number).first()
        if ticket:
            logger.info(f"Retrieved ticket {ticket_number}")
        else:
            logger.warning(f"Ticket {ticket_number} not found")
        return ticket
    
    def update_ticket(self, ticket_id: int, ticket_update: TicketUpdate) -> Optional[Ticket]:
        """Update ticket information."""
        ticket = self.db.query(Ticket).filter(Ticket.id == ticket_id).first()
        if not ticket:
            logger.warning(f"Ticket {ticket_id} not found for update")
            return None
        
        update_data = ticket_update.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(ticket, field, value)
        
        ticket.updated_at = datetime.utcnow()
        
        # Set resolved_at if status is resolved or closed
        if ticket_update.status in ["resolved", "closed"] and not ticket.resolved_at:
            ticket.resolved_at = datetime.utcnow()
        
        self.db.commit()
        self.db.refresh(ticket)
        
        logger.info(f"Updated ticket {ticket_id}")
        return ticket
    
    def search_tickets(
        self,
        query: str,
        technician_email: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 20
    ) -> List[Ticket]:
        """Search tickets by query string."""
        try:
            # First, let's check if there are any tickets at all
            total_tickets = self.db.query(Ticket).count()
            logger.info(f"Total tickets in database: {total_tickets}")
            
            # Create search filter with case-insensitive search
            search_filter = or_(
                Ticket.title.ilike(f"%{query}%"),
                Ticket.description.ilike(f"%{query}%"),
                Ticket.ticketnumber.ilike(f"%{query}%"),
                Ticket.issuetype.ilike(f"%{query}%"),
                Ticket.ticketcategory.ilike(f"%{query}%"),
                Ticket.subissuetype.ilike(f"%{query}%")
            )

            # First, search for tickets assigned to the technician
            assigned_tickets = []
            if technician_email:
                assigned_query = self.db.query(Ticket).filter(
                    and_(search_filter, Ticket.technicianemail == technician_email)
                ).limit(limit).all()
                assigned_tickets = assigned_tickets + assigned_query
                logger.info(f"Found {len(assigned_tickets)} tickets assigned to technician: {technician_email}")

            # If we have enough assigned tickets, return them
            if len(assigned_tickets) >= limit:
                logger.info(f"Returning {len(assigned_tickets)} assigned tickets for query: '{query}'")
                return assigned_tickets[:limit]
            
            # If we don't have enough assigned tickets, also search for similar unassigned tickets
            remaining_limit = limit - len(assigned_tickets)
            if remaining_limit > 0:
                # Search for similar tickets that are not assigned to this technician
                unassigned_query = self.db.query(Ticket).filter(
                    and_(
                        search_filter,
                        or_(
                            Ticket.technicianemail.is_(None),
                            Ticket.technicianemail != technician_email
                        )
                    )
                ).limit(remaining_limit).all()
                
                logger.info(f"Found {len(unassigned_query)} similar unassigned tickets")
                
                # Combine assigned and similar unassigned tickets
                all_tickets = assigned_tickets + unassigned_query
                logger.info(f"Total tickets found: {len(all_tickets)} for query: '{query}'")
                return all_tickets
            
            # If still no results, try a broader search without technician filter
            if len(assigned_tickets) == 0:
                logger.info(f"No tickets found for query '{query}', trying broader search...")
                broader_tickets = self.db.query(Ticket).filter(search_filter).limit(limit).all()
                logger.info(f"Broader search found {len(broader_tickets)} tickets for query: '{query}'")
                return broader_tickets
            
            return assigned_tickets
            
        except Exception as e:
            logger.error(f"Error searching tickets: {e}")
            return []

    def find_similar_tickets_by_issue(self, issue_description: str, limit: int = 10) -> List[Ticket]:
        """Find similar tickets using semantic similarity from both TICKETS and COMPANY_4130_DATA tables."""
        try:
            logger.info(f"Searching for similar tickets with description: '{issue_description}'")
            
            # Use raw SQL for semantic similarity search since SQLAlchemy doesn't support Snowflake Cortex functions
            # Get the engine directly for raw SQL execution
            from ..database import create_snowflake_engine
            engine = create_snowflake_engine()
            
            # Search in TICKETS table using semantic similarity
            tickets_query = f"""
                SELECT 
                    TICKETNUMBER,
                    TITLE,
                    DESCRIPTION,
                    STATUS,
                    PRIORITY,
                    TECHNICIANEMAIL,
                    ISSUETYPE,
                    SUBISSUETYPE,
                    RESOLUTION,
                    TICKETTYPE,
                    TICKETCATEGORY,
                    SNOWFLAKE.CORTEX.AI_SIMILARITY(
                        COALESCE(TITLE, '') || ' ' || COALESCE(DESCRIPTION, ''),
                        '{issue_description.replace("'", "''")}'
                    ) AS SIMILARITY_SCORE
                FROM TEST_DB.PUBLIC.TICKETS
                WHERE TITLE IS NOT NULL
                AND DESCRIPTION IS NOT NULL
                AND TRIM(TITLE) != ''
                AND TRIM(DESCRIPTION) != ''
                AND LENGTH(TRIM(TITLE || ' ' || DESCRIPTION)) > 10
                ORDER BY SIMILARITY_SCORE DESC
                LIMIT {limit}
            """
            
            # Search in COMPANY_4130_DATA table using semantic similarity
            # Note: Using only the columns that exist in COMPANY_4130_DATA table
            company_query = f"""
                SELECT 
                    TICKETNUMBER,
                    TITLE,
                    DESCRIPTION,
                    STATUS,
                    PRIORITY,
                    ISSUETYPE,
                    SUBISSUETYPE,
                    RESOLUTION,
                    TICKETTYPE,
                    TICKETCATEGORY,
                    SNOWFLAKE.CORTEX.AI_SIMILARITY(
                        COALESCE(TITLE, '') || ' ' || COALESCE(DESCRIPTION, ''),
                        '{issue_description.replace("'", "''")}'
                    ) AS SIMILARITY_SCORE
                FROM TEST_DB.PUBLIC.COMPANY_4130_DATA
                WHERE TITLE IS NOT NULL
                AND DESCRIPTION IS NOT NULL
                AND TRIM(TITLE) != ''
                AND TRIM(DESCRIPTION) != ''
                AND LENGTH(TRIM(TITLE || ' ' || DESCRIPTION)) > 10
                ORDER BY SIMILARITY_SCORE DESC
                LIMIT {limit}
            """
            
            # Execute queries using raw SQL
            from sqlalchemy import text
            with engine.connect() as connection:
                tickets_results = connection.execute(text(tickets_query)).fetchall()
                company_results = connection.execute(text(company_query)).fetchall()
                
            # Convert results to dictionaries for easier access
            tickets_dicts = [dict(row._mapping) for row in tickets_results]
            company_dicts = [dict(row._mapping) for row in company_results]
            
            # Combine and sort results by similarity score
            all_results = []
            
            # Process TICKETS results
            for row in tickets_dicts:
                score = row.get('SIMILARITY_SCORE', 0)
                if isinstance(score, (int, float)) and score >= 0.1:  # Minimum similarity threshold
                    # Create Ticket object from row
                    ticket = Ticket(
                        ticketnumber=row.get('TICKETNUMBER'),
                        title=row.get('TITLE'),
                        description=row.get('DESCRIPTION'),
                        status=row.get('STATUS'),
                        priority=row.get('PRIORITY'),
                        technicianemail=row.get('TECHNICIANEMAIL'),
                        issuetype=row.get('ISSUETYPE'),
                        subissuetype=row.get('SUBISSUETYPE'),
                        resolution=row.get('RESOLUTION'),
                        tickettype=row.get('TICKETTYPE'),
                        ticketcategory=row.get('TICKETCATEGORY')
                    )
                    all_results.append((ticket, score, 'TICKETS'))
            
            # Process COMPANY_4130_DATA results
            for row in company_dicts:
                score = row.get('SIMILARITY_SCORE', 0)
                if isinstance(score, (int, float)) and score >= 0.1:  # Minimum similarity threshold
                    # Create Ticket object from row (using same model for compatibility)
                    ticket = Ticket(
                        ticketnumber=row.get('TICKETNUMBER'),
                        title=row.get('TITLE'),
                        description=f"[Source: COMPANY_4130_DATA] {row.get('DESCRIPTION', '')}",
                        status=row.get('STATUS'),
                        priority=row.get('PRIORITY'),
                        technicianemail=None,  # COMPANY_4130_DATA doesn't have this column
                        issuetype=row.get('ISSUETYPE'),
                        subissuetype=row.get('SUBISSUETYPE'),
                        resolution=row.get('RESOLUTION'),
                        tickettype=row.get('TICKETTYPE'),
                        ticketcategory=row.get('TICKETCATEGORY')
                    )
                    all_results.append((ticket, score, 'COMPANY_4130_DATA'))
            
            # Sort by similarity score (highest first)
            all_results.sort(key=lambda x: x[1], reverse=True)
            
            logger.info(f"Found {len(all_results)} similar tickets for issue: {issue_description}")
            
            # Return top tickets
            return [ticket for ticket, score, source in all_results[:limit]]
            
        except Exception as e:
            logger.error(f"Failed to find similar tickets with semantic similarity: {e}")
            # Fallback to keyword-based search
            return self._find_similar_tickets_fallback(issue_description, limit)

    def _find_similar_tickets_fallback(self, issue_description: str, limit: int = 10) -> List[Ticket]:
        """Fallback method for finding similar tickets using keyword-based search."""
        try:
            logger.info(f"Using fallback keyword search for: '{issue_description}'")
            
            # Split the issue description into keywords for better matching
            keywords = [word.strip() for word in issue_description.split() if len(word.strip()) > 2]
            logger.info(f"Extracted keywords: {keywords}")
            
            # If no keywords found, try with shorter words
            if not keywords:
                keywords = [word.strip() for word in issue_description.split() if len(word.strip()) > 1]
                logger.info(f"Using shorter keywords: {keywords}")
            
            # Create search filters for each keyword
            search_filters = []
            for keyword in keywords[:5]:  # Limit to first 5 keywords to avoid too complex queries
                keyword_filter = or_(
                    Ticket.title.ilike(f"%{keyword}%"),
                    Ticket.description.ilike(f"%{keyword}%"),
                    Ticket.issuetype.ilike(f"%{keyword}%"),
                    Ticket.subissuetype.ilike(f"%{keyword}%"),
                    Ticket.ticketcategory.ilike(f"%{keyword}%")
                )
                search_filters.append(keyword_filter)
                logger.info(f"Added filter for keyword: {keyword}")
            
            # Combine all keyword filters
            if search_filters:
                combined_filter = or_(*search_filters)
                logger.info(f"Using keyword-based search with {len(search_filters)} filters")
            else:
                # Fallback to original description search
                combined_filter = or_(
                    Ticket.title.ilike(f"%{issue_description}%"),
                    Ticket.description.ilike(f"%{issue_description}%"),
                    Ticket.issuetype.ilike(f"%{issue_description}%"),
                    Ticket.subissuetype.ilike(f"%{issue_description}%")
                )
                logger.info("Using fallback search with original description")
            
            # Search for similar tickets
            similar_tickets = self.db.query(Ticket).filter(combined_filter).limit(limit).all()

            logger.info(f"Found {len(similar_tickets)} similar tickets for issue: {issue_description}")
            
            # If still no results, try a very broad search
            if len(similar_tickets) == 0:
                logger.info("No results found, trying very broad search...")
                # Try searching just the first word or issue type
                if keywords:
                    broad_search = self.db.query(Ticket).filter(
                        Ticket.issuetype.ilike(f"%{keywords[0]}%")
                    ).limit(limit).all()
                    logger.info(f"Broad search found {len(broad_search)} tickets")
                    return broad_search
            
            return similar_tickets
        except Exception as e:
            logger.error(f"Failed to find similar tickets in fallback: {e}")
            return []

    def get_tickets_by_status(
        self,
        status: str,
        technician_email: Optional[str] = None,
        limit: int = 50
    ) -> List[Ticket]:
        """Get tickets by status (resolved/open)."""
        if status == "resolved":
            query_obj = self.db.query(Ticket).filter(Ticket.resolution.isnot(None))
        else:
            query_obj = self.db.query(Ticket).filter(
                or_(Ticket.resolution.is_(None), Ticket.resolution == "")
            )

        if technician_email:
            query_obj = query_obj.filter(Ticket.technicianemail == technician_email)

        tickets = query_obj.limit(limit).all()

        logger.info(f"Retrieved {len(tickets)} tickets with status {status}")
        return tickets
    
    def assign_ticket(self, ticket_id: int, technician_id: int) -> Optional[Ticket]:
        """Assign ticket to a technician."""
        ticket = self.db.query(Ticket).filter(Ticket.id == ticket_id).first()
        if not ticket:
            logger.warning(f"Ticket {ticket_id} not found for assignment")
            return None
        
        ticket.assigned_technician_id = technician_id
        ticket.updated_at = datetime.utcnow()
        
        # Update status to in_progress if it's currently open
        if ticket.status == "open":
            ticket.status = "in_progress"
        
        self.db.commit()
        self.db.refresh(ticket)
        
        logger.info(f"Assigned ticket {ticket_id} to technician {technician_id}")
        return ticket

    def debug_search_sample(self, query: str = "email", limit: int = 5):
        """Debug method to see what tickets contain the search term."""
        try:
            logger.info(f"Debug: Searching for '{query}' in all tickets...")
            
            # Search in title
            title_matches = self.db.query(Ticket).filter(Ticket.title.ilike(f"%{query}%")).limit(limit).all()
            logger.info(f"Debug: Found {len(title_matches)} tickets with '{query}' in title")
            for ticket in title_matches:
                logger.info(f"Debug: Title match - {ticket.ticketnumber}: {ticket.title}")
            
            # Search in description
            desc_matches = self.db.query(Ticket).filter(Ticket.description.ilike(f"%{query}%")).limit(limit).all()
            logger.info(f"Debug: Found {len(desc_matches)} tickets with '{query}' in description")
            for ticket in desc_matches:
                logger.info(f"Debug: Description match - {ticket.ticketnumber}: {ticket.description[:100]}...")
            
            # Search in issue type
            issue_matches = self.db.query(Ticket).filter(Ticket.issuetype.ilike(f"%{query}%")).limit(limit).all()
            logger.info(f"Debug: Found {len(issue_matches)} tickets with '{query}' in issue type")
            for ticket in issue_matches:
                logger.info(f"Debug: Issue type match - {ticket.ticketnumber}: {ticket.issuetype}")
            
            # Show some sample tickets
            sample_tickets = self.db.query(Ticket).limit(3).all()
            logger.info(f"Debug: Sample tickets in database:")
            for ticket in sample_tickets:
                logger.info(f"Debug: {ticket.ticketnumber} - Title: {ticket.title}, Issue: {ticket.issuetype}")
                
        except Exception as e:
            logger.error(f"Debug search error: {e}")
