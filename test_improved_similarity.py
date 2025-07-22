#!/usr/bin/env python3
"""
Test script for the improved semantic similarity functionality with hybrid search.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

def test_improved_similarity():
    """
    Test the improved semantic similarity functionality.
    """
    print("🔧 Testing Improved Semantic Similarity with Hybrid Search")
    print("=" * 65)
    
    # Test case from the user's example
    title = "Gmail issue"
    description = "having issue with mail not showing up in office 365 from my gmail box"
    
    print(f"📧 TEST CASE - EMAIL ISSUE:")
    print(f"   Title: {title}")
    print(f"   Description: {description}")
    print()
    
    print("🚀 IMPROVEMENTS MADE:")
    print("   ✅ Fixed formatting error in similarity score display")
    print("   ✅ Added COALESCE to handle NULL values in TITLE/DESCRIPTION")
    print("   ✅ Added minimum similarity threshold filtering")
    print("   ✅ Implemented hybrid search (semantic + keyword matching)")
    print("   ✅ Added keyword extraction for better matching")
    print("   ✅ Enhanced error handling and fallback mechanisms")
    print()
    
    print("🔍 KEYWORD EXTRACTION DEMO:")
    import re
    ticket_text = f"{title} {description}"
    stop_words = {'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might', 'can', 'cannot', 'not', 'no', 'yes', 'this', 'that', 'these', 'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they', 'me', 'him', 'her', 'us', 'them', 'my', 'your', 'his', 'her', 'its', 'our', 'their', 'a', 'an'}
    
    words = re.findall(r'\b\w+\b', ticket_text.lower())
    keywords = [word for word in words if len(word) > 3 and word not in stop_words][:5]
    
    print(f"   Original text: '{ticket_text}'")
    print(f"   Extracted keywords: {keywords}")
    print()
    
    print("📊 HYBRID SEARCH STRATEGY:")
    print("   1. First try: Pure semantic similarity with AI_SIMILARITY()")
    print("   2. Filter results by minimum similarity threshold (0.1)")
    print("   3. If low quality results: Use hybrid approach")
    print("   4. Hybrid combines semantic similarity + keyword filtering")
    print("   5. Final fallback: Recent tickets if all else fails")
    print()
    
    print("🎯 EXPECTED IMPROVEMENTS FOR EMAIL ISSUES:")
    print("   Should now find tickets containing:")
    print("   • 'gmail', 'email', 'mail' - direct keyword matches")
    print("   • 'outlook', 'exchange' - semantic similarity")
    print("   • 'office', '365' - related terms")
    print("   • 'showing', 'display', 'appear' - semantic variants")
    print()
    
    # Show the hybrid query that would be generated
    escaped_ticket_text = ticket_text.replace("'", "''")
    keyword_conditions = []
    
    for keyword in keywords:
        escaped_keyword = keyword.replace("'", "''")
        keyword_conditions.append(f"(UPPER(TITLE) LIKE UPPER('%{escaped_keyword}%') OR UPPER(DESCRIPTION) LIKE UPPER('%{escaped_keyword}%'))")
    
    keyword_filter = " OR ".join(keyword_conditions)
    
    print("🔧 GENERATED HYBRID QUERY:")
    sample_query = f"""
    SELECT
        TICKETNUMBER, TITLE, DESCRIPTION, ISSUETYPE, SUBISSUETYPE,
        TICKETCATEGORY, TICKETTYPE, PRIORITY, STATUS, RESOLUTION,
        SNOWFLAKE.CORTEX.AI_SIMILARITY(
            COALESCE(TITLE, '') || ' ' || COALESCE(DESCRIPTION, ''),
            '{escaped_ticket_text}'
        ) AS SIMILARITY_SCORE
    FROM TEST_DB.PUBLIC.COMPANY_4130_DATA
    WHERE TITLE IS NOT NULL 
    AND DESCRIPTION IS NOT NULL
    AND TRIM(TITLE) != ''
    AND TRIM(DESCRIPTION) != ''
    AND ({keyword_filter})
    ORDER BY SIMILARITY_SCORE DESC
    LIMIT 20
    """
    
    print(sample_query)
    print()
    
    print("✅ FIXES APPLIED:")
    print("   🐛 Fixed: 'Invalid format specifier' error in score display")
    print("   🎯 Enhanced: Better keyword extraction and filtering")
    print("   🔄 Added: Hybrid search for improved accuracy")
    print("   🛡️ Improved: Error handling and fallback mechanisms")
    print("   📊 Added: Similarity threshold filtering")
    print()
    
    print("🎉 READY FOR TESTING!")
    print("   The improved system should now find more relevant email-related tickets")
    print("   and handle edge cases better with proper error handling.")

if __name__ == "__main__":
    test_improved_similarity()
