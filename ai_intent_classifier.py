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
            # Personal Data Intent
            IntentPrototype(
                intent=QueryIntent.PERSONAL_DATA,
                phrases=[
                    "show me my bookings",
                    "what are my appointments",
                    "my profile information",
                    "my account details",
                    "list my orders",
                    "show my booking history",
                    "what bookings do I have",
                    "my personal data",
                    "my user information",
                    "show me my profile",
                    "what's in my account",
                    "my scheduled appointments",
                    "bookings under my name",
                    "my reservation details"
                ],
                requires_firebase=True,
                suggested_collections=["users", "Booking", "bookings"]
            ),
            
            # General Info / Policy Questions
            IntentPrototype(
                intent=QueryIntent.GENERAL_INFO,
                phrases=[
                    "what is the refund policy",
                    "how do refunds work",
                    "when do interpreters get paid",
                    "payment terms for interpreters",
                    "invoicing process",
                    "how to submit an invoice",
                    "who approves refunds",
                    "what is the cancellation policy",
                    "company policies",
                    "payment schedule",
                    "how long until payment",
                    "refund approval process",
                    "invoice submission deadline",
                    "payment conditions",
                    "what happens if I cancel"
                ],
                requires_firebase=False,
                suggested_collections=[]
            ),
            
            # Payment Info
            IntentPrototype(
                intent=QueryIntent.GENERAL_INFO,
                phrases=[
                    "when will I get paid",
                    "payment processing time",
                    "how long for payment",
                    "payment delay reasons",
                    "why is payment late",
                    "payment schedule for interpreters",
                    "when are invoices paid",
                    "payment timeline",
                    "how soon will I receive payment",
                    "what if I leave a job halfway",
                    "incomplete assignment payment",
                    "partial work payment"
                ],
                requires_firebase=False,
                suggested_collections=[]
            ),
            
            # Booking Info (could be personal or general)
            IntentPrototype(
                intent=QueryIntent.PERSONAL_DATA,
                phrases=[
                    "my upcoming bookings",
                    "when is my next appointment",
                    "booking status",
                    "my confirmed bookings",
                    "cancelled bookings",
                    "pending bookings",
                    "booking details",
                    "my scheduled jobs"
                ],
                requires_firebase=True,
                suggested_collections=["Booking", "bookings"]
            ),
            
            # Greeting / Small Talk
            IntentPrototype(
                intent=QueryIntent.UNKNOWN,
                phrases=[
                    "hello",
                    "hi there",
                    "good morning",
                    "how are you",
                    "thanks",
                    "thank you",
                    "goodbye",
                    "bye"
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
