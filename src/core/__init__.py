"""
Core functionality package for TeamLogic-AutoTask.
Contains email processing, ticket handling, and page controllers.
"""

from .email_processor import EmailProcessor
from .ticket_handlers import TicketHandlers
from .page_controllers import PageControllers

__all__ = [
    'EmailProcessor',
    'TicketHandlers', 
    'PageControllers'
]
