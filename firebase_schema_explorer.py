"""
Firebase Schema Explorer Module
================================
Recursively explores entire Firestore database structure in READ-ONLY mode.
Discovers all collections, documents, fields, and subcollections.
Caches schema to JSON file for performance.

SECURITY: This module is STRICTLY READ-ONLY.
- Only uses .get(), .stream(), .collections()
- NO write/update/delete operations
- NO data mutation of any kind
"""

import os
import json
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional, Set
from pathlib import Path

import firebase_admin
from firebase_admin import credentials, firestore
from google.cloud.firestore_v1.base_document import DocumentSnapshot

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Schema cache file path
SCHEMA_CACHE_FILE = "firebase_schema.json"

# Maximum documents to sample per collection (for field discovery)
MAX_SAMPLE_DOCS = 5

# Maximum depth for subcollection traversal (prevent infinite loops)
MAX_DEPTH = 10


class FirebaseSchemaExplorer:
    """
    Explores Firestore database structure in READ-ONLY mode.
    
    SECURITY GUARANTEES:
    - Only read operations are performed
    - No data modification is possible through this class
    - All write methods are explicitly blocked
    """
    
    def __init__(self, credentials_path: Optional[str] = None):
        """
        Initialize Firebase connection with READ-ONLY intent.
        
        Args:
            credentials_path: Path to Firebase Admin SDK JSON file
        """
        self._db = None
        self._schema: Dict[str, Any] = {}
        self._discovered_paths: Set[str] = set()
        
        # Initialize Firebase if not already done
        self._initialize_firebase(credentials_path)
    
    def _initialize_firebase(self, credentials_path: Optional[str] = None) -> None:
        """Initialize Firebase Admin SDK."""
        if firebase_admin._apps:
            # Already initialized
            self._db = firestore.client()
            logger.info("Using existing Firebase connection")
            return
        
        # Get credentials path from parameter or environment
        cred_path = credentials_path or os.getenv("FIREBASE_CREDENTIALS_PATH")
        
        if not cred_path:
            raise ValueError(
                "Firebase credentials path not provided. "
                "Set FIREBASE_CREDENTIALS_PATH environment variable or pass credentials_path parameter."
            )
        
        if not os.path.exists(cred_path):
            raise FileNotFoundError(f"Firebase credentials file not found: {cred_path}")
        
        # Initialize with service account
        cred = credentials.Certificate(cred_path)
        firebase_admin.initialize_app(cred)
        self._db = firestore.client()
        
        logger.info(f"Firebase initialized from: {cred_path}")
    
    # =========================================================================
    # SECURITY: BLOCK ALL WRITE OPERATIONS
    # =========================================================================
    
    def _block_write_operation(self, operation_name: str) -> None:
        """Raise error for any write operation attempt."""
        raise PermissionError(
            f"SECURITY VIOLATION: Write operation '{operation_name}' is BLOCKED. "
            f"This module is READ-ONLY. No data modification is allowed."
        )
    
    def set(self, *args, **kwargs):
        self._block_write_operation("set")
    
    def update(self, *args, **kwargs):
        self._block_write_operation("update")
    
    def delete(self, *args, **kwargs):
        self._block_write_operation("delete")
    
    def add(self, *args, **kwargs):
        self._block_write_operation("add")
    
    def create(self, *args, **kwargs):
        self._block_write_operation("create")
    
    def batch(self, *args, **kwargs):
        self._block_write_operation("batch")
    
    def transaction(self, *args, **kwargs):
        self._block_write_operation("transaction")
    
    # =========================================================================
    # READ-ONLY SCHEMA DISCOVERY
    # =========================================================================
    
    def discover_schema(self, force_refresh: bool = False) -> Dict[str, Any]:
        """
        Discover complete Firestore schema.
        
        This method:
        1. Checks for cached schema first
        2. If no cache or force_refresh, explores entire database
        3. Saves discovered schema to cache file
        
        Args:
            force_refresh: If True, ignore cache and rediscover
            
        Returns:
            Complete schema dictionary
        """
        # Check cache first
        if not force_refresh and os.path.exists(SCHEMA_CACHE_FILE):
            try:
                with open(SCHEMA_CACHE_FILE, 'r') as f:
                    cached = json.load(f)
                    logger.info(f"Loaded schema from cache: {SCHEMA_CACHE_FILE}")
                    self._schema = cached
                    return cached
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"Cache read failed, will rediscover: {e}")
        
        # Discover schema
        logger.info("Starting Firestore schema discovery (READ-ONLY)...")
        
        self._schema = {
            "discovered_at": datetime.utcnow().isoformat(),
            "collections": {},
            "total_collections": 0,
            "total_documents_sampled": 0,
            "total_fields_discovered": 0,
            "total_subcollections": 0
        }
        
        self._discovered_paths.clear()
        
        # Get all root collections (READ-ONLY operation)
        root_collections = self._db.collections()
        
        for collection_ref in root_collections:
            self._explore_collection(collection_ref, depth=0)
        
        # Update totals
        self._schema["total_collections"] = len(self._schema["collections"])
        
        # Save to cache
        self._save_schema_cache()
        
        logger.info(
            f"Schema discovery complete: "
            f"{self._schema['total_collections']} collections, "
            f"{self._schema['total_documents_sampled']} documents sampled, "
            f"{self._schema['total_fields_discovered']} fields discovered"
        )
        
        return self._schema
    
    def _explore_collection(self, collection_ref, depth: int, parent_path: str = "") -> None:
        """
        Recursively explore a collection and its subcollections.
        
        READ-ONLY: Only uses .stream() and .collections()
        
        Args:
            collection_ref: Firestore collection reference
            depth: Current recursion depth
            parent_path: Path of parent for nested collections
        """
        if depth > MAX_DEPTH:
            logger.warning(f"Max depth {MAX_DEPTH} reached, stopping recursion")
            return
        
        collection_name = collection_ref.id
        full_path = f"{parent_path}/{collection_name}" if parent_path else collection_name
        
        # Avoid re-exploring same path
        if full_path in self._discovered_paths:
            return
        self._discovered_paths.add(full_path)
        
        logger.info(f"[Exploring] {full_path}")
        
        collection_schema = {
            "path": full_path,
            "fields": {},
            "field_types": {},
            "sample_document_ids": [],
            "subcollections": {},
            "document_count_sampled": 0
        }
        
        # Sample documents to discover fields (READ-ONLY: using .stream())
        docs_sampled = 0
        all_fields: Dict[str, Set[str]] = {}  # field_name -> set of types
        
        try:
            # Limit to MAX_SAMPLE_DOCS for performance
            for doc in collection_ref.limit(MAX_SAMPLE_DOCS).stream():
                docs_sampled += 1
                self._schema["total_documents_sampled"] += 1
                
                collection_schema["sample_document_ids"].append(doc.id)
                
                # Extract field information (READ-ONLY: using .to_dict())
                doc_data = doc.to_dict()
                if doc_data:
                    for field_name, field_value in doc_data.items():
                        field_type = self._get_field_type(field_value)
                        
                        if field_name not in all_fields:
                            all_fields[field_name] = set()
                        all_fields[field_name].add(field_type)
                
                # Discover subcollections (READ-ONLY: using .collections())
                for subcoll_ref in doc.reference.collections():
                    subcoll_name = subcoll_ref.id
                    if subcoll_name not in collection_schema["subcollections"]:
                        collection_schema["subcollections"][subcoll_name] = {
                            "discovered_in_doc": doc.id
                        }
                        self._schema["total_subcollections"] += 1
                        
                        # Recursively explore subcollection
                        self._explore_collection(
                            subcoll_ref,
                            depth=depth + 1,
                            parent_path=f"{full_path}/{doc.id}"
                        )
        
        except Exception as e:
            logger.error(f"Error exploring {full_path}: {e}")
        
        # Consolidate field information
        for field_name, types in all_fields.items():
            collection_schema["fields"][field_name] = list(types)
            self._schema["total_fields_discovered"] += 1
        
        collection_schema["document_count_sampled"] = docs_sampled
        
        # Store in schema
        self._schema["collections"][full_path] = collection_schema
    
    def _get_field_type(self, value: Any) -> str:
        """Determine the type of a field value."""
        if value is None:
            return "null"
        elif isinstance(value, bool):
            return "boolean"
        elif isinstance(value, int):
            return "integer"
        elif isinstance(value, float):
            return "number"
        elif isinstance(value, str):
            return "string"
        elif isinstance(value, list):
            return "array"
        elif isinstance(value, dict):
            return "map"
        elif hasattr(value, 'seconds'):  # Timestamp
            return "timestamp"
        elif hasattr(value, 'latitude'):  # GeoPoint
            return "geopoint"
        elif hasattr(value, 'path'):  # DocumentReference
            return "reference"
        else:
            return "unknown"
    
    def _save_schema_cache(self) -> None:
        """Save discovered schema to JSON cache file."""
        try:
            with open(SCHEMA_CACHE_FILE, 'w') as f:
                json.dump(self._schema, f, indent=2, default=str)
            logger.info(f"Schema cached to: {SCHEMA_CACHE_FILE}")
        except IOError as e:
            logger.error(f"Failed to cache schema: {e}")
    
    # =========================================================================
    # SCHEMA ACCESS METHODS (READ-ONLY)
    # =========================================================================
    
    def get_schema(self) -> Dict[str, Any]:
        """Get the discovered schema."""
        if not self._schema or not self._schema.get("collections"):
            return self.discover_schema()
        return self._schema
    
    def get_collections(self) -> List[str]:
        """Get list of all collection paths."""
        schema = self.get_schema()
        return list(schema.get("collections", {}).keys())
    
    def get_collection_fields(self, collection_path: str) -> Dict[str, List[str]]:
        """Get fields for a specific collection."""
        schema = self.get_schema()
        collection = schema.get("collections", {}).get(collection_path, {})
        return collection.get("fields", {})
    
    def get_subcollections(self, collection_path: str) -> List[str]:
        """Get subcollections for a collection."""
        schema = self.get_schema()
        collection = schema.get("collections", {}).get(collection_path, {})
        return list(collection.get("subcollections", {}).keys())
    
    def collection_exists(self, collection_path: str) -> bool:
        """Check if a collection exists in the schema."""
        schema = self.get_schema()
        return collection_path in schema.get("collections", {})
    
    def field_exists(self, collection_path: str, field_name: str) -> bool:
        """Check if a field exists in a collection."""
        fields = self.get_collection_fields(collection_path)
        return field_name in fields
    
    def find_collections_with_field(self, field_name: str) -> List[str]:
        """Find all collections that have a specific field."""
        schema = self.get_schema()
        matching = []
        for path, collection in schema.get("collections", {}).items():
            if field_name in collection.get("fields", {}):
                matching.append(path)
        return matching
    
    def get_schema_summary(self) -> str:
        """Get a human-readable schema summary."""
        schema = self.get_schema()
        
        lines = [
            "=" * 60,
            "FIRESTORE SCHEMA SUMMARY",
            "=" * 60,
            f"Discovered at: {schema.get('discovered_at', 'Unknown')}",
            f"Total collections: {schema.get('total_collections', 0)}",
            f"Total documents sampled: {schema.get('total_documents_sampled', 0)}",
            f"Total fields discovered: {schema.get('total_fields_discovered', 0)}",
            f"Total subcollections: {schema.get('total_subcollections', 0)}",
            "",
            "COLLECTIONS:",
            "-" * 40
        ]
        
        for path, collection in schema.get("collections", {}).items():
            fields = collection.get("fields", {})
            subcollections = collection.get("subcollections", {})
            
            lines.append(f"\n📁 {path}")
            lines.append(f"   Documents sampled: {collection.get('document_count_sampled', 0)}")
            lines.append(f"   Fields ({len(fields)}):")
            
            for field_name, field_types in fields.items():
                types_str = ", ".join(field_types) if isinstance(field_types, list) else field_types
                lines.append(f"      • {field_name}: {types_str}")
            
            if subcollections:
                lines.append(f"   Subcollections ({len(subcollections)}):")
                for subcoll_name in subcollections:
                    lines.append(f"      └── {subcoll_name}/")
        
        lines.append("\n" + "=" * 60)
        return "\n".join(lines)


# =============================================================================
# STANDALONE FUNCTIONS FOR EASY ACCESS
# =============================================================================

_explorer_instance: Optional[FirebaseSchemaExplorer] = None


def get_schema_explorer(credentials_path: Optional[str] = None) -> FirebaseSchemaExplorer:
    """Get or create the schema explorer singleton."""
    global _explorer_instance
    if _explorer_instance is None:
        _explorer_instance = FirebaseSchemaExplorer(credentials_path)
    return _explorer_instance


def discover_firestore_schema(force_refresh: bool = False) -> Dict[str, Any]:
    """Discover and return the Firestore schema."""
    explorer = get_schema_explorer()
    return explorer.discover_schema(force_refresh)


def get_firestore_schema() -> Dict[str, Any]:
    """Get the cached or discovered Firestore schema."""
    explorer = get_schema_explorer()
    return explorer.get_schema()


def get_collection_list() -> List[str]:
    """Get list of all Firestore collections."""
    explorer = get_schema_explorer()
    return explorer.get_collections()


# =============================================================================
# MAIN - For standalone testing
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("FIRESTORE SCHEMA EXPLORER (READ-ONLY)")
    print("=" * 60)
    
    try:
        explorer = FirebaseSchemaExplorer()
        schema = explorer.discover_schema(force_refresh=True)
        print(explorer.get_schema_summary())
        
        print("\n✓ Schema discovery complete!")
        print(f"✓ Cached to: {SCHEMA_CACHE_FILE}")
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        raise
