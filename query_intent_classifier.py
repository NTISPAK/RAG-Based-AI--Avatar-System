"""
Query Intent Classifier Module
===============================
Analyzes user queries to determine if they require personal Firebase data.
Uses pattern matching and keyword analysis to classify intent.

This module helps the RAG system decide:
1. Whether to query Firebase (personal data needed)
2. Which collections to query
3. What fields might be relevant
"""

import re
import logging
from typing import Dict, List, Tuple, Optional, Set
from dataclasses import dataclass, field
from enum import Enum

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class QueryIntent(Enum):
    """Types of query intent."""
    PERSONAL_DATA = "personal_data"      # User wants their own data
    GENERAL_INFO = "general_info"        # General policy/info questions
    MIXED = "mixed"                      # Both personal and general
    UNKNOWN = "unknown"


@dataclass
class IntentClassification:
    """Result of intent classification."""
    intent: QueryIntent
    confidence: float  # 0.0 to 1.0
    requires_firebase: bool
    suggested_collections: List[str] = field(default_factory=list)
    suggested_fields: List[str] = field(default_factory=list)
    matched_patterns: List[str] = field(default_factory=list)
    user_id_required: bool = False
    explanation: str = ""


class QueryIntentClassifier:
    """
    Classifies user queries to determine if Firebase data is needed.
    
    Classification is based on:
    1. Personal pronouns and possessives
    2. Action verbs related to user data
    3. Entity keywords (bookings, orders, profile, etc.)
    4. Question patterns
    """
    
    # =========================================================================
    # PATTERN DEFINITIONS
    # =========================================================================
    
    # Personal pronouns and possessives that indicate user-specific data
    PERSONAL_INDICATORS = {
        "my", "mine", "i", "me", "myself",
        "i'm", "i've", "i'd", "i'll",
        "our", "ours", "we", "us"
    }
    
    # Action verbs that typically involve personal data
    PERSONAL_ACTION_VERBS = {
        "show", "display", "list", "get", "fetch", "retrieve",
        "find", "check", "view", "see", "look",
        "have", "own", "made", "placed", "created",
        "booked", "ordered", "purchased", "subscribed",
        "updated", "changed", "modified"
    }
    
    # Entity keywords that map to collections
    ENTITY_COLLECTION_MAP = {
        # Booking related
        "booking": ["Booking", "bookings"],
        "bookings": ["Booking", "bookings"],
        "appointment": ["Booking", "bookings"],
        "appointments": ["Booking", "bookings"],
        "reservation": ["Booking", "bookings"],
        "reservations": ["Booking", "bookings"],
        "service": ["Booking", "bookings"],
        "services": ["Booking", "bookings"],
        
        # Order related
        "order": ["Booking", "bookings", "orders"],
        "orders": ["Booking", "bookings", "orders"],
        "purchase": ["Booking", "bookings", "orders"],
        "purchases": ["Booking", "bookings", "orders"],
        
        # User/Profile related
        "profile": ["users"],
        "account": ["users"],
        "details": ["users"],
        "information": ["users"],
        "info": ["users"],
        "data": ["users"],
        
        # Notification related
        "notification": ["notifications", "adminNotification"],
        "notifications": ["notifications", "adminNotification"],
        "alert": ["notifications"],
        "alerts": ["notifications"],
        "message": ["notifications"],
        "messages": ["notifications"],
        
        # Payment related
        "payment": ["Booking", "bookings", "payments"],
        "payments": ["Booking", "bookings", "payments"],
        "invoice": ["Booking", "bookings", "invoices"],
        "invoices": ["Booking", "bookings", "invoices"],
        "bill": ["Booking", "bookings"],
        "bills": ["Booking", "bookings"],
        
        # Subscription related
        "subscription": ["subscriptions", "users"],
        "subscriptions": ["subscriptions", "users"],
        "plan": ["subscriptions", "users"],
        "membership": ["subscriptions", "users"],
        
        # History related
        "history": ["Booking", "bookings", "users"],
        "past": ["Booking", "bookings"],
        "previous": ["Booking", "bookings"],
        "recent": ["Booking", "bookings"],
    }
    
    # Field keywords that map to specific fields
    FIELD_KEYWORDS = {
        "name": ["name", "displayName", "full_name", "firstName", "lastName"],
        "email": ["email", "emailAddress"],
        "phone": ["phone", "phoneNumber", "mobile", "contact"],
        "address": ["address", "location", "city", "country"],
        "status": ["status", "state", "bookingStatus"],
        "date": ["date", "createdAt", "updatedAt", "bookingDate"],
        "time": ["time", "startTime", "endTime"],
        "price": ["price", "amount", "total", "cost"],
        "company": ["company", "companyName", "organization"],
    }
    
    # Patterns that indicate personal data queries
    PERSONAL_PATTERNS = [
        r"\bmy\s+\w+",                          # "my bookings", "my profile"
        r"\bshow\s+me\b",                       # "show me"
        r"\bwhat\s+(?:is|are)\s+my\b",          # "what is my", "what are my"
        r"\bdo\s+i\s+have\b",                   # "do I have"
        r"\bhow\s+many\s+(?:\w+\s+)?(?:do\s+)?i\b",  # "how many orders do I"
        r"\bi\s+(?:have|made|placed|booked)\b", # "I have", "I made"
        r"\bwhen\s+(?:did|was|is)\s+my\b",      # "when did my", "when was my"
        r"\bwhere\s+is\s+my\b",                 # "where is my"
        r"\bcan\s+i\s+(?:see|view|check)\b",    # "can I see", "can I view"
        r"\blist\s+(?:all\s+)?my\b",            # "list my", "list all my"
        r"\bget\s+my\b",                        # "get my"
        r"\bfetch\s+my\b",                      # "fetch my"
        r"\bfind\s+my\b",                       # "find my"
        r"\bcheck\s+my\b",                      # "check my"
        r"\bview\s+my\b",                       # "view my"
        r"\blook\s+(?:at|up)\s+my\b",           # "look at my", "look up my"
        r"\bam\s+i\b",                          # "am I subscribed"
        r"\bhave\s+i\b",                        # "have I booked"
        r"\bdid\s+i\b",                         # "did I order"
    ]
    
    # Patterns that indicate general/policy questions (NOT personal)
    GENERAL_PATTERNS = [
        r"\bwhat\s+is\s+(?:the|a)\b",           # "what is the policy"
        r"\bhow\s+(?:does|do)\s+(?:the|a)\b",   # "how does the system"
        r"\bwhat\s+are\s+(?:the|your)\b",       # "what are the rules"
        r"\bexplain\b",                         # "explain the process"
        r"\btell\s+me\s+about\b",               # "tell me about" (without "my")
        r"\bwhat\s+happens\s+(?:if|when)\b",    # "what happens if"
        r"\bcan\s+(?:you|someone)\b",           # "can you explain"
        r"\bpolicy\b",                          # mentions "policy"
        r"\brule[s]?\b",                        # mentions "rules"
        r"\bprocedure[s]?\b",                   # mentions "procedures"
        r"\bprocess\b",                         # mentions "process"
        r"\bgeneral(?:ly)?\b",                  # "generally", "general"
    ]
    
    def __init__(self, schema: Optional[Dict] = None):
        """
        Initialize the classifier.
        
        Args:
            schema: Optional Firestore schema for collection validation
        """
        self._schema = schema
        self._available_collections: Set[str] = set()
        
        if schema:
            self._available_collections = set(schema.get("collections", {}).keys())
    
    def set_schema(self, schema: Dict) -> None:
        """Update the schema for collection validation."""
        self._schema = schema
        self._available_collections = set(schema.get("collections", {}).keys())
    
    def classify(self, query: str) -> IntentClassification:
        """
        Classify a user query to determine intent.
        
        Args:
            query: The user's query string
            
        Returns:
            IntentClassification with detailed analysis
        """
        query_lower = query.lower().strip()
        words = set(re.findall(r'\b\w+\b', query_lower))
        
        # Initialize scores
        personal_score = 0.0
        general_score = 0.0
        matched_patterns = []
        suggested_collections = set()
        suggested_fields = set()
        
        # Check for personal indicators
        personal_words = words & self.PERSONAL_INDICATORS
        if personal_words:
            personal_score += 0.3 * len(personal_words)
            matched_patterns.extend([f"personal_word:{w}" for w in personal_words])
        
        # Check for personal action verbs
        action_words = words & self.PERSONAL_ACTION_VERBS
        if action_words and personal_words:
            personal_score += 0.2 * len(action_words)
            matched_patterns.extend([f"action_verb:{w}" for w in action_words])
        
        # Check for entity keywords
        for word in words:
            if word in self.ENTITY_COLLECTION_MAP:
                collections = self.ENTITY_COLLECTION_MAP[word]
                # Filter to available collections
                for coll in collections:
                    if self._collection_available(coll):
                        suggested_collections.add(coll)
                matched_patterns.append(f"entity:{word}")
                
                # If combined with personal indicator, boost score
                if personal_words:
                    personal_score += 0.2
        
        # Check for field keywords
        for word in words:
            if word in self.FIELD_KEYWORDS:
                suggested_fields.update(self.FIELD_KEYWORDS[word])
                matched_patterns.append(f"field:{word}")
        
        # Check personal patterns (regex)
        for pattern in self.PERSONAL_PATTERNS:
            if re.search(pattern, query_lower):
                personal_score += 0.25
                matched_patterns.append(f"pattern:{pattern[:30]}")
        
        # Check general patterns (regex)
        for pattern in self.GENERAL_PATTERNS:
            if re.search(pattern, query_lower):
                general_score += 0.2
                matched_patterns.append(f"general_pattern:{pattern[:30]}")
        
        # Normalize scores
        personal_score = min(personal_score, 1.0)
        general_score = min(general_score, 1.0)
        
        # Determine intent
        if personal_score >= 0.4 and personal_score > general_score:
            intent = QueryIntent.PERSONAL_DATA
            confidence = personal_score
            requires_firebase = True
            user_id_required = True
            explanation = "Query contains personal data indicators"
        elif general_score >= 0.3 and general_score > personal_score:
            intent = QueryIntent.GENERAL_INFO
            confidence = general_score
            requires_firebase = False
            user_id_required = False
            explanation = "Query appears to be a general information request"
        elif personal_score >= 0.2 and general_score >= 0.2:
            intent = QueryIntent.MIXED
            confidence = max(personal_score, general_score)
            requires_firebase = personal_score >= 0.3
            user_id_required = requires_firebase
            explanation = "Query may involve both personal and general information"
        else:
            intent = QueryIntent.UNKNOWN
            confidence = 0.5
            requires_firebase = False
            user_id_required = False
            explanation = "Unable to determine clear intent"
        
        # If no collections suggested but Firebase required, suggest common ones
        if requires_firebase and not suggested_collections:
            suggested_collections = self._get_default_user_collections()
        
        return IntentClassification(
            intent=intent,
            confidence=confidence,
            requires_firebase=requires_firebase,
            suggested_collections=list(suggested_collections),
            suggested_fields=list(suggested_fields),
            matched_patterns=matched_patterns,
            user_id_required=user_id_required,
            explanation=explanation
        )
    
    def _collection_available(self, collection_name: str) -> bool:
        """Check if a collection is available in the schema."""
        if not self._available_collections:
            return True  # No schema, assume available
        
        # Check exact match or partial match
        for available in self._available_collections:
            if collection_name == available or available.endswith(f"/{collection_name}"):
                return True
            if collection_name.lower() == available.lower():
                return True
        
        return False
    
    def _get_default_user_collections(self) -> Set[str]:
        """Get default collections for user data."""
        defaults = {"users", "Booking", "bookings"}
        
        if self._available_collections:
            return defaults & self._available_collections
        
        return defaults
    
    def should_query_firebase(
        self,
        query: str,
        confidence_threshold: float = 0.3
    ) -> Tuple[bool, IntentClassification]:
        """
        Determine if a query should trigger Firebase read.
        
        Args:
            query: User query string
            confidence_threshold: Minimum confidence to trigger Firebase
            
        Returns:
            Tuple of (should_query, classification)
        """
        classification = self.classify(query)
        
        should_query = (
            classification.requires_firebase and
            classification.confidence >= confidence_threshold
        )
        
        return should_query, classification


# =============================================================================
# STANDALONE FUNCTIONS
# =============================================================================

_classifier_instance: Optional[QueryIntentClassifier] = None


def get_classifier(schema: Optional[Dict] = None) -> QueryIntentClassifier:
    """Get or create the classifier singleton."""
    global _classifier_instance
    if _classifier_instance is None:
        _classifier_instance = QueryIntentClassifier(schema)
    elif schema:
        _classifier_instance.set_schema(schema)
    return _classifier_instance


def classify_query(query: str, schema: Optional[Dict] = None) -> IntentClassification:
    """Classify a query's intent."""
    classifier = get_classifier(schema)
    return classifier.classify(query)


def should_query_firebase(
    query: str,
    confidence_threshold: float = 0.3,
    schema: Optional[Dict] = None
) -> Tuple[bool, IntentClassification]:
    """Determine if a query should trigger Firebase read."""
    classifier = get_classifier(schema)
    return classifier.should_query_firebase(query, confidence_threshold)


def get_suggested_collections(query: str, schema: Optional[Dict] = None) -> List[str]:
    """Get suggested collections for a query."""
    classification = classify_query(query, schema)
    return classification.suggested_collections


# =============================================================================
# MAIN - For standalone testing
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("QUERY INTENT CLASSIFIER TEST")
    print("=" * 60)
    
    # Test queries
    test_queries = [
        # Personal data queries
        "Show me my bookings",
        "What is my profile information?",
        "How many orders do I have?",
        "List all my appointments",
        "Check my account status",
        "When was my last booking?",
        "Do I have any pending payments?",
        "What services have I booked?",
        
        # General queries
        "What is the refund policy?",
        "How does the payment system work?",
        "Explain the booking process",
        "What are the cancellation rules?",
        "Tell me about interpreter payments",
        
        # Mixed/Ambiguous
        "Can I get a refund for my booking?",
        "What happens if I cancel my order?",
        "How do I update my profile?",
    ]
    
    classifier = QueryIntentClassifier()
    
    for query in test_queries:
        print(f"\n{'─' * 50}")
        print(f"Query: \"{query}\"")
        
        classification = classifier.classify(query)
        
        print(f"Intent: {classification.intent.value}")
        print(f"Confidence: {classification.confidence:.2f}")
        print(f"Requires Firebase: {classification.requires_firebase}")
        print(f"User ID Required: {classification.user_id_required}")
        print(f"Suggested Collections: {classification.suggested_collections}")
        print(f"Explanation: {classification.explanation}")
    
    print("\n" + "=" * 60)
    print("✓ Classification test complete!")
