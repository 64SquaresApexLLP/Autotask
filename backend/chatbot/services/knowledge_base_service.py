"""Knowledge base service for FAQ and help articles."""

import logging
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
from ..database import KnowledgeBase

logger = logging.getLogger(__name__)


class KnowledgeBaseService:
    """Service for managing knowledge base articles and FAQ functionality."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def search_articles(self, query: str, category: Optional[str] = None, limit: int = 10) -> List[KnowledgeBase]:
        """Search knowledge base articles by query and optional category."""
        try:
            # Build search conditions
            search_conditions = []
            
            if query:
                query_lower = query.lower()
                search_conditions.extend([
                    KnowledgeBase.title.ilike(f"%{query}%"),
                    KnowledgeBase.content.ilike(f"%{query}%"),
                    KnowledgeBase.tags.ilike(f"%{query}%")
                ])
            
            # Start with base query
            query_builder = self.db.query(KnowledgeBase).filter(
                KnowledgeBase.is_published == True
            )
            
            # Add search conditions if any
            if search_conditions:
                query_builder = query_builder.filter(or_(*search_conditions))
            
            # Add category filter if specified
            if category:
                query_builder = query_builder.filter(
                    KnowledgeBase.category.ilike(f"%{category}%")
                )
            
            # Order by view count (popularity) and limit results
            articles = query_builder.order_by(
                KnowledgeBase.view_count.desc(),
                KnowledgeBase.created_at.desc()
            ).limit(limit).all()
            
            return articles
            
        except Exception as e:
            logger.error(f"Error searching knowledge base: {e}")
            return []
    
    def get_all_categories(self) -> List[str]:
        """Get all unique categories from knowledge base."""
        try:
            categories = self.db.query(KnowledgeBase.category).filter(
                and_(
                    KnowledgeBase.is_published == True,
                    KnowledgeBase.category.isnot(None),
                    KnowledgeBase.category != ""
                )
            ).distinct().all()
            
            return [cat[0] for cat in categories if cat[0]]
            
        except Exception as e:
            logger.error(f"Error getting categories: {e}")
            return []
    
    def get_popular_articles(self, limit: int = 10) -> List[KnowledgeBase]:
        """Get most popular knowledge base articles."""
        try:
            articles = self.db.query(KnowledgeBase).filter(
                KnowledgeBase.is_published == True
            ).order_by(
                KnowledgeBase.view_count.desc(),
                KnowledgeBase.created_at.desc()
            ).limit(limit).all()
            
            return articles
            
        except Exception as e:
            logger.error(f"Error getting popular articles: {e}")
            return []
    
    def get_article_by_id(self, article_id: int) -> Optional[KnowledgeBase]:
        """Get specific knowledge base article by ID."""
        try:
            article = self.db.query(KnowledgeBase).filter(
                and_(
                    KnowledgeBase.id == article_id,
                    KnowledgeBase.is_published == True
                )
            ).first()
            
            # Increment view count if article found
            if article:
                article.view_count = (article.view_count or 0) + 1
                self.db.commit()
            
            return article
            
        except Exception as e:
            logger.error(f"Error getting article {article_id}: {e}")
            return None
    
    def find_faq_by_keywords(self, keywords: List[str], limit: int = 5) -> List[KnowledgeBase]:
        """Find FAQ articles by keywords."""
        try:
            if not keywords:
                return self.get_popular_articles(limit)
            
            # Build search conditions for keywords
            search_conditions = []
            for keyword in keywords:
                search_conditions.extend([
                    KnowledgeBase.title.ilike(f"%{keyword}%"),
                    KnowledgeBase.content.ilike(f"%{keyword}%"),
                    KnowledgeBase.tags.ilike(f"%{keyword}%"),
                    KnowledgeBase.category.ilike(f"%{keyword}%")
                ])
            
            articles = self.db.query(KnowledgeBase).filter(
                and_(
                    KnowledgeBase.is_published == True,
                    or_(*search_conditions)
                )
            ).order_by(
                KnowledgeBase.view_count.desc()
            ).limit(limit).all()
            
            return articles
            
        except Exception as e:
            logger.error(f"Error finding FAQ by keywords: {e}")
            return []
    
    def create_article(self, title: str, content: str, category: Optional[str] = None,
                      tags: Optional[str] = None, author_id: Optional[str] = None) -> Optional[KnowledgeBase]:
        """Create a new knowledge base article."""
        try:
            article = KnowledgeBase(
                title=title,
                content=content,
                category=category,
                tags=tags,
                author_id=author_id,
                view_count=0,
                is_published=True
            )
            
            self.db.add(article)
            self.db.commit()
            self.db.refresh(article)
            
            logger.info(f"Created knowledge base article: {title}")
            return article
            
        except Exception as e:
            logger.error(f"Error creating article: {e}")
            self.db.rollback()
            return None
    
    def update_article(self, article_id: int, title: Optional[str] = None, content: Optional[str] = None,
                      category: Optional[str] = None, tags: Optional[str] = None) -> Optional[KnowledgeBase]:
        """Update an existing knowledge base article."""
        try:
            article = self.db.query(KnowledgeBase).filter(
                KnowledgeBase.id == article_id
            ).first()
            
            if not article:
                return None
            
            # Update fields if provided
            if title is not None:
                article.title = title
            if content is not None:
                article.content = content
            if category is not None:
                article.category = category
            if tags is not None:
                article.tags = tags
            
            # Update timestamp
            from datetime import datetime
            article.updated_at = datetime.utcnow()
            
            self.db.commit()
            self.db.refresh(article)
            
            logger.info(f"Updated knowledge base article: {article_id}")
            return article
            
        except Exception as e:
            logger.error(f"Error updating article {article_id}: {e}")
            self.db.rollback()
            return None
    
    def delete_article(self, article_id: int) -> bool:
        """Delete (unpublish) a knowledge base article."""
        try:
            article = self.db.query(KnowledgeBase).filter(
                KnowledgeBase.id == article_id
            ).first()
            
            if not article:
                return False
            
            # Soft delete by unpublishing
            article.is_published = False
            self.db.commit()
            
            logger.info(f"Deleted (unpublished) knowledge base article: {article_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting article {article_id}: {e}")
            self.db.rollback()
            return False
    
    def get_articles_by_category(self, category: str, limit: int = 10) -> List[KnowledgeBase]:
        """Get articles by specific category."""
        try:
            articles = self.db.query(KnowledgeBase).filter(
                and_(
                    KnowledgeBase.is_published == True,
                    KnowledgeBase.category.ilike(f"%{category}%")
                )
            ).order_by(
                KnowledgeBase.view_count.desc(),
                KnowledgeBase.created_at.desc()
            ).limit(limit).all()
            
            return articles
            
        except Exception as e:
            logger.error(f"Error getting articles by category {category}: {e}")
            return []
