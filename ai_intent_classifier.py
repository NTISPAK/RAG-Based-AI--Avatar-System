"""
AI-Based Intent Classifier using Sentence Embeddings
=====================================================
Uses semantic similarity between query and prototype phrases to classify intent.
Falls back to rule-based classifier if confidence is too low.

This approach:
1. Encodes the user query using HuggingFace embeddings
2. Compares it to prototype phrases for each intent
3. Returns the intent with highest similarity score
4. Falls back to rule-based classifier if similarity is below threshold
"""

import logging
from typing import Dict, List, Tuple, Set, Optional
from dataclasses import dataclass
import numpy as np
from sentence_transformers import SentenceTransformer

from query_intent_classifier import (
    QueryIntent,
    IntentClassification,
    QueryIntentClassifier as RuleBasedClassifier
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class IntentPrototype:
    """Prototype phrases for an intent."""
    intent: QueryIntent
    phrases: List[str]
    requires_firebase: bool
    suggested_collections: List[str]


class AIIntentClassifier:
    """
    AI-based intent classifier using sentence embeddings.
    
    Uses semantic similarity to match queries to intent prototypes.
    Falls back to rule-based classifier when confidence is low.
    """
    
    def __init__(
        self,
        schema: Optional[Dict] = None,
        model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
        fallback_threshold: float = 0.4
    ):
        """
        Initialize the AI intent classifier.
        
        Args:
            schema: Firebase schema (optional)
            model_name: HuggingFace model for embeddings
            fallback_threshold: Minimum similarity to trust AI classification
        """
        self.schema = schema
        self.fallback_threshold = fallback_threshold
        
        # Initialize embedding model
        logger.info(f"Loading embedding model: {model_name}")
        self.model = SentenceTransformer(model_name)
        
        # Initialize fallback rule-based classifier
        self.fallback_classifier = RuleBasedClassifier(schema)
        
        # Define intent prototypes
        self.prototypes = self._create_prototypes()
        
        # Pre-compute prototype embeddings
        self._compute_prototype_embeddings()
        
        logger.info(f"AI Intent Classifier initialized with {len(self.prototypes)} intent prototypes")
    
    def _create_prototypes(self) -> List[IntentPrototype]:
        """Create prototype phrases for each intent."""
        return [
            # Personal Data Intent - Account / Profile / Orders / Bookings
            IntentPrototype(
                intent=QueryIntent.PERSONAL_DATA,
                phrases=[
                    # Direct Booking Access
                    "show me my bookings",
                    "show my bookings",
                    "list my bookings",
                    "display my bookings",
                    "get my bookings",
                    "retrieve my bookings",
                    "view my bookings",
                    "check my bookings",
                    "fetch my bookings",
                    "what are my bookings",
                    "what bookings do I have",
                    "do I have any bookings",
                    "let me see my bookings",
                    "can you show my bookings",
                    "please show my bookings",
                    "I want to see my bookings",
                    "I need to see my bookings",
                    
                    # Booking History
                    "my booking history",
                    "show my booking history",
                    "view my booking history",
                    "my past bookings",
                    "my previous bookings",
                    "my recent bookings",
                    
                    # Booking Details
                    "my booking details",
                    "show my booking details",
                    "details of my booking",
                    "bookings under my name",
                    "bookings linked to me",
                    "bookings in my account",
                    
                    # Appointments
                    "what are my appointments",
                    "show my appointments",
                    "list my appointments",
                    "view my appointments",
                    "my appointments",
                    "do I have any appointments",
                    "my scheduled appointments",
                    "my upcoming appointments",
                    "my confirmed appointments",
                    "when is my next appointment",
                    "what is my next appointment",
                    
                    # Orders
                    "list my orders",
                    "show my orders",
                    "view my orders",
                    "what orders do I have",
                    "my order history",
                    
                    # Profile
                    "my profile information",
                    "show me my profile",
                    "show my profile",
                    "view my profile",
                    "check my profile",
                    "my profile details",
                    
                    # Account
                    "my account details",
                    "show my account details",
                    "view my account details",
                    "what's in my account",
                    "my account information",
                    
                    # Personal Data
                    "my personal data",
                    "my personal information",
                    "my user information",
                    "my user details",
                    "what data do you have about me"
                ],
                requires_firebase=True,
                suggested_collections=["users", "Booking", "bookings"]
            ),
            
            # General Info / Policy Questions - Refund / Cancellation / Invoicing
            IntentPrototype(
                intent=QueryIntent.GENERAL_INFO,
                phrases=[
                    # Refund Policy
                    "what is the refund policy",
                    "explain the refund policy",
                    "tell me the refund policy",
                    "how does the refund policy work",
                    "refund policy details",
                    "refund rules",
                    "refund terms",
                    "refund conditions",
                    "how do refunds work",
                    "how are refunds processed",
                    "how are refunds approved",
                    "who approves refunds",
                    "refund approval process",
                    "can I get a refund",
                    "am I eligible for a refund",
                    "how long do refunds take",
                    
                    # Cancellation Policy
                    "what is the cancellation policy",
                    "cancellation policy details",
                    "cancellation rules",
                    "what happens if I cancel",
                    "what happens if a booking is cancelled",
                    "cancellation conditions",
                    "booking cancellation rules",
                    
                    # Invoicing
                    "invoicing process",
                    "how does invoicing work",
                    "how to submit an invoice",
                    "how do I submit an invoice",
                    "invoice submission process",
                    "invoice submission deadline",
                    "when is the invoice due",
                    "where do I submit my invoice",
                    "how are invoices processed",
                    "invoice approval process",
                    "invoice requirements",
                    "steps to submit an invoice",
                    
                    # Company Policies
                    "company policies",
                    "company rules",
                    "business policies",
                    "terms and conditions",
                    "service policies",
                    "general policies",
                    
                    # Payment Policy
                    "payment policy",
                    "payment conditions",
                    "payment terms for interpreters",
                    "interpreter payment terms",
                    "how does payment work",
                    "payment schedule",
                    "payment rules",
                    "how are interpreters paid"
                ],
                requires_firebase=False,
                suggested_collections=[]
            ),
            
            # Payment Info - Timing / Delay / Partial Work
            IntentPrototype(
                intent=QueryIntent.GENERAL_INFO,
                phrases=[
                    # Payment Timing
                    "when will I get paid",
                    "when do I get paid",
                    "when will payment be made",
                    "how long does payment take",
                    "how long until I get paid",
                    "payment processing time",
                    "payment timeline",
                    "expected payment date",
                    "when are invoices paid",
                    "how soon will I receive payment",
                    "how soon will I be paid",
                    "payment turnaround time",
                    "invoice payment time",
                    "interpreter payment schedule",
                    
                    # Payment Delays
                    "payment delay reasons",
                    "why is payment late",
                    "why is my payment delayed",
                    "reason for delayed payment",
                    "what causes payment delays",
                    "why hasn't payment arrived",
                    "delay in payment processing",
                    "late payment explanation",
                    
                    # Partial Work
                    "what if I leave a job halfway",
                    "incomplete assignment payment",
                    "partial work payment",
                    "do I get paid for partial work",
                    "payment for incomplete job",
                    "will I get paid if I leave early",
                    "payment for half completed job",
                    "how is partial work paid",
                    "do interpreters get paid for partial work",
                    "what happens if I do not finish a job",
                    "payment for unfinished assignment"
                ],
                requires_firebase=False,
                suggested_collections=[]
            ),
            
            # Booking Status Focused
            IntentPrototype(
                intent=QueryIntent.PERSONAL_DATA,
                phrases=[
                    "my upcoming bookings",
                    "show my upcoming bookings",
                    "list my upcoming bookings",
                    "what bookings are coming up for me",
                    "my next booking",
                    "what is my next booking",
                    "when is my next appointment",
                    "tell me my next booking",
                    "booking status",
                    "check booking status",
                    "what is the status of my booking",
                    "status of my upcoming booking",
                    "my confirmed bookings",
                    "show my confirmed bookings",
                    "my pending bookings",
                    "show my pending bookings",
                    "my cancelled bookings",
                    "show my cancelled bookings",
                    "booking details",
                    "show my booking details",
                    "details of my booking",
                    "my scheduled jobs",
                    "jobs I have scheduled",
                    "jobs assigned to me",
                    "appointments assigned to me"
                ],
                requires_firebase=True,
                suggested_collections=["Booking", "bookings"]
            ),
            
            # Greeting / Small Talk
            IntentPrototype(
                intent=QueryIntent.UNKNOWN,
                phrases=[
                    "hello",
                    "hi",
                    "hi there",
                    "hey",
                    "hello there",
                    "good morning",
                    "good afternoon",
                    "good evening",
                    "greetings",
                    "how are you",
                    "how's it going",
                    "what's up",
                    "how have you been",
                    "nice to meet you",
                    "thanks",
                    "thank you",
                    "thanks a lot",
                    "many thanks",
                    "appreciate it",
                    "goodbye",
                    "bye",
                    "see you",
                    "see you later",
                    "talk later",
                    "take care"
                ],
                requires_firebase=False,
                suggested_collections=[]
            )
        ]
    
    def _compute_prototype_embeddings(self):
        """Pre-compute embeddings for all prototype phrases."""
        self.prototype_embeddings = []
        self.prototype_metadata = []
        
        for prototype in self.prototypes:
            for phrase in prototype.phrases:
                # Encode phrase
                embedding = self.model.encode(phrase, normalize_embeddings=True)
                
                # Store embedding and metadata
                self.prototype_embeddings.append(embedding)
                self.prototype_metadata.append({
                    'intent': prototype.intent,
                    'requires_firebase': prototype.requires_firebase,
                    'suggested_collections': prototype.suggested_collections,
                    'phrase': phrase
                })
        
        # Convert to numpy array for efficient computation
        self.prototype_embeddings = np.array(self.prototype_embeddings)
        
        logger.info(f"Computed {len(self.prototype_embeddings)} prototype embeddings")
    
    def classify(self, query: str) -> IntentClassification:
        """
        Classify query intent using semantic similarity.
        
        Args:
            query: User query string
            
        Returns:
            IntentClassification with intent, confidence, and metadata
        """
        try:
            # Encode query
            query_embedding = self.model.encode(query, normalize_embeddings=True)
            
            # Compute cosine similarity with all prototypes
            similarities = np.dot(self.prototype_embeddings, query_embedding)
            
            # Find best match
            best_idx = np.argmax(similarities)
            best_similarity = similarities[best_idx]
            best_metadata = self.prototype_metadata[best_idx]
            
            logger.info(f"[AI Classifier] Query: '{query[:50]}...'")
            logger.info(f"[AI Classifier] Best match: '{best_metadata['phrase']}' (similarity: {best_similarity:.3f})")
            
            # Check if confidence is high enough
            if best_similarity >= self.fallback_threshold:
                # Use AI classification
                return IntentClassification(
                    intent=best_metadata['intent'],
                    confidence=float(best_similarity),
                    requires_firebase=best_metadata['requires_firebase'],
                    suggested_collections=best_metadata['suggested_collections']
                )
            else:
                # Confidence too low, fall back to rule-based
                logger.warning(f"[AI Classifier] Low confidence ({best_similarity:.3f}), falling back to rule-based classifier")
                return self.fallback_classifier.classify(query)
                
        except Exception as e:
            logger.error(f"[AI Classifier] Error: {e}, falling back to rule-based classifier")
            return self.fallback_classifier.classify(query)
    
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
# SINGLETON INSTANCE
# =============================================================================

_classifier_instance: Optional[AIIntentClassifier] = None


def get_ai_classifier(schema: Optional[Dict] = None) -> AIIntentClassifier:
    """Get or create the AI classifier singleton."""
    global _classifier_instance
    if _classifier_instance is None:
        _classifier_instance = AIIntentClassifier(schema)
    return _classifier_instance


def classify_query_ai(query: str, schema: Optional[Dict] = None) -> IntentClassification:
    """Classify a query using AI-based classifier."""
    classifier = get_ai_classifier(schema)
    return classifier.classify(query)


def should_query_firebase_ai(
    query: str,
    confidence_threshold: float = 0.3,
    schema: Optional[Dict] = None
) -> Tuple[bool, IntentClassification]:
    """Determine if query should trigger Firebase using AI classifier."""
    classifier = get_ai_classifier(schema)
    return classifier.should_query_firebase(query, confidence_threshold)


# =============================================================================
# TESTING
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("AI INTENT CLASSIFIER TEST")
    print("=" * 60)
    
    # Initialize classifier
    classifier = AIIntentClassifier()
    
    # Test queries
    test_queries = [
        "What is the refund policy?",
        "Show me my bookings",
        "When do interpreters get paid?",
        "What are my upcoming appointments?",
        "How do I submit an invoice?",
        "What happens if I leave a job halfway?",
        "My profile information",
        "Hello, how are you?",
        "What's the weather like today?",
        "Can I get a refund if I cancel?"
    ]
    
    print("\nTesting AI-based classification:\n")
    for query in test_queries:
        classification = classifier.classify(query)
        print(f"Query: {query}")
        print(f"  Intent: {classification.intent.value}")
        print(f"  Confidence: {classification.confidence:.3f}")
        print(f"  Requires Firebase: {classification.requires_firebase}")
        print(f"  Collections: {classification.suggested_collections}")
        print()
