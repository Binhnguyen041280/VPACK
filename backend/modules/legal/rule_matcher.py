"""
Rule Matcher Module

Matches legal rules to arbitration cases based on dispute type, category, and content.
"""

import logging
from typing import List, Dict, Any, Optional
from .knowledge_base import LegalKnowledgeBase

logger = logging.getLogger(__name__)


class RuleMatcher:
    """
    Matches legal rules to cases
    """

    def __init__(self):
        """Initialize Rule Matcher"""
        self.kb = LegalKnowledgeBase()
        self.logger = logger

    def find_applicable_rules(
        self,
        dispute_type: str,
        description: str,
        respondent_type: str = 'platform',
        jurisdiction: str = 'VN'
    ) -> List[Dict[str, Any]]:
        """
        Find applicable legal rules for a case

        Args:
            dispute_type: Type of dispute (refund, ban, payment, etc.)
            description: Case description
            respondent_type: Type of respondent (platform, buyer, etc.)
            jurisdiction: Jurisdiction code

        Returns:
            List of applicable rules
        """
        try:
            applicable_rules = []

            # 1. Search by category (map dispute_type to category)
            category_mapping = {
                'refund': 'refund',
                'ban': 'account_suspension',
                'payment': 'payment',
                'quality': 'product_quality',
                'fraud': 'fraud',
                'shipping': 'shipping'
            }

            category = category_mapping.get(dispute_type)

            if category:
                rules = self.kb.search_rules(category=category, jurisdiction=jurisdiction)
                applicable_rules.extend(rules)

            # 2. Search by keyword in description
            keywords = self._extract_keywords(description)
            for keyword in keywords:
                rules = self.kb.search_rules(query=keyword, jurisdiction=jurisdiction)
                applicable_rules.extend(rules)

            # 3. Get platform-specific rules
            if respondent_type == 'platform':
                platform_rules = self.kb.search_rules(rule_type='platform', jurisdiction=jurisdiction)
                applicable_rules.extend(platform_rules)

            # 4. Get general commercial law rules
            commercial_rules = self.kb.search_rules(
                rule_type='commercial_law',
                jurisdiction=jurisdiction,
                limit=10
            )
            applicable_rules.extend(commercial_rules)

            # Remove duplicates (by rule_id)
            seen_ids = set()
            unique_rules = []
            for rule in applicable_rules:
                if rule['rule_id'] not in seen_ids:
                    unique_rules.append(rule)
                    seen_ids.add(rule['rule_id'])

            self.logger.info(f"✅ Found {len(unique_rules)} applicable rules")

            return unique_rules[:20]  # Limit to top 20

        except Exception as e:
            self.logger.error(f"Error finding applicable rules: {e}")
            return []

    def _extract_keywords(self, text: str) -> List[str]:
        """
        Extract keywords from text for rule matching

        Args:
            text: Input text

        Returns:
            List of keywords
        """
        # Simple keyword extraction (can be enhanced with NLP)
        important_words = [
            'hoàn tiền', 'hoàn trả', 'khóa tài khoản', 'vi phạm',
            'gian lận', 'hàng giả', 'sai mô tả', 'không giao hàng',
            'muộn', 'chậm trễ', 'bồi thường', 'thiệt hại',
            'refund', 'ban', 'fraud', 'fake', 'scam', 'delay', 'damage'
        ]

        keywords = []
        text_lower = text.lower()

        for word in important_words:
            if word in text_lower:
                keywords.append(word)

        return keywords[:5]  # Top 5 keywords

    def rank_rules_by_relevance(
        self,
        rules: List[Dict[str, Any]],
        case_description: str
    ) -> List[Dict[str, Any]]:
        """
        Rank rules by relevance to case

        Args:
            rules: List of rules
            case_description: Case description

        Returns:
            Ranked list of rules
        """
        # Simple ranking (can be enhanced with ML)
        ranked_rules = []

        for rule in rules:
            score = 0

            # Higher score for exact category match
            # Higher score for keyword matches in content
            # Higher score for platform rules

            if rule['rule_type'] == 'platform':
                score += 10

            # Count keyword matches
            keywords = self._extract_keywords(case_description)
            for keyword in keywords:
                if keyword in rule['content'].lower():
                    score += 5

            ranked_rules.append({
                **rule,
                'relevance_score': score
            })

        # Sort by score descending
        ranked_rules.sort(key=lambda x: x['relevance_score'], reverse=True)

        return ranked_rules
