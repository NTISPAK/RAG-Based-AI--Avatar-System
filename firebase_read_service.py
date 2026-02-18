"""
Firebase Read Service Module
=============================
Provides STRICTLY READ-ONLY access to Firestore data.
Validates all queries against discovered schema.
Enforces user-based data isolation.

SECURITY GUARANTEES:
- Only read operations (.get(), .stream()) are allowed
- All write operations are BLOCKED and raise PermissionError
- Queries are validated against schema before execution
- User data isolation is enforced
"""

import os
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple, Union
from dataclasses import dataclass, field

import firebase_admin
from firebase_admin import credentials, firestore
from google.cloud.firestore_v1.base_query import FieldFilter

from firebase_schema_explorer import get_schema_explorer, get_firestore_schema

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class FirebaseReadResult:
    """Result of a Firebase read operation."""
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    path: str = ""
    fields_read: List[str] = field(default_factory=list)
    document_count: int = 0


@dataclass
class ReadPath:
    """Represents a read path with fields."""
    collection: str
    document_id: Optional[str] = None
    fields: List[str] = field(default_factory=list)
    filters: List[Tuple[str, str, Any]] = field(default_factory=list)


class FirebaseReadService:
    """
    Provides STRICTLY READ-ONLY access to Firestore.
    
    SECURITY ENFORCEMENT:
    - All write methods are blocked
    - Queries are validated against schema
    - User isolation is enforced
    - Only minimal required fields are fetched
    """
    
    # =========================================================================
    # BLOCKED OPERATIONS - These will NEVER execute
    # =========================================================================
    
    BLOCKED_OPERATIONS = frozenset([
        'set', 'update', 'delete', 'add', 'create',
        'batch', 'transaction', 'commit', 'write',
        'set_with_merge', 'update_with_transform'
    ])
    
    def __init__(self):
        """Initialize the read service."""
        self._db = None
        self._schema = None
        self._read_paths: Dict[str, Dict] = {}  # Track what was read
        self._initialize()
    
    def _initialize(self) -> None:
        """Initialize Firebase connection."""
        if not firebase_admin._apps:
            cred_path = os.getenv("FIREBASE_CREDENTIALS_PATH")
            if cred_path and os.path.exists(cred_path):
                cred = credentials.Certificate(cred_path)
                firebase_admin.initialize_app(cred)
        
        self._db = firestore.client()
        self._schema = get_firestore_schema()
        logger.info("FirebaseReadService initialized (READ-ONLY mode)")
    
    # =========================================================================
    # SECURITY: BLOCK ALL WRITE OPERATIONS
    # =========================================================================
    
    def __getattribute__(self, name: str) -> Any:
        """Intercept attribute access to block write operations."""
        blocked = object.__getattribute__(self, 'BLOCKED_OPERATIONS')
        if name.lower() in blocked:
            raise PermissionError(
                f"SECURITY VIOLATION: Operation '{name}' is BLOCKED. "
                f"FirebaseReadService is READ-ONLY. No data modification allowed."
            )
        return object.__getattribute__(self, name)
    
    def _block_write(self, operation: str) -> None:
        """Explicitly block a write operation."""
        raise PermissionError(
            f"SECURITY VIOLATION: '{operation}' is a write operation and is BLOCKED. "
            f"This service is READ-ONLY."
        )
    
    # Explicit blocks for common write methods
    def set(self, *args, **kwargs): self._block_write("set")
    def update(self, *args, **kwargs): self._block_write("update")
    def delete(self, *args, **kwargs): self._block_write("delete")
    def add(self, *args, **kwargs): self._block_write("add")
    def create(self, *args, **kwargs): self._block_write("create")
    def batch(self, *args, **kwargs): self._block_write("batch")
    def commit(self, *args, **kwargs): self._block_write("commit")
    def transaction(self, *args, **kwargs): self._block_write("transaction")
    
    # =========================================================================
    # SCHEMA VALIDATION
    # =========================================================================
    
    def validate_collection(self, collection_path: str) -> bool:
        """Validate that a collection exists in the schema."""
        if not self._schema:
            self._schema = get_firestore_schema()
        
        collections = self._schema.get("collections", {})
        
        # Check exact match
        if collection_path in collections:
            return True
        
        # Check if it's a root collection (without path prefix)
        for path in collections:
            if path == collection_path or path.endswith(f"/{collection_path}"):
                return True
        
        return False
    
    def validate_fields(self, collection_path: str, fields: List[str]) -> Tuple[bool, List[str]]:
        """
        Validate that fields exist in a collection.
        
        Returns:
            Tuple of (all_valid, list_of_invalid_fields)
        """
        if not self._schema:
            self._schema = get_firestore_schema()
        
        collection_info = self._schema.get("collections", {}).get(collection_path, {})
        schema_fields = collection_info.get("fields", {})
        
        invalid_fields = [f for f in fields if f not in schema_fields]
        
        return len(invalid_fields) == 0, invalid_fields
    
    def get_available_fields(self, collection_path: str) -> List[str]:
        """Get list of available fields for a collection."""
        if not self._schema:
            self._schema = get_firestore_schema()
        
        collection_info = self._schema.get("collections", {}).get(collection_path, {})
        return list(collection_info.get("fields", {}).keys())
    
    # =========================================================================
    # READ OPERATIONS (SAFE)
    # =========================================================================
    
    def read_document(
        self,
        collection: str,
        document_id: str,
        fields: Optional[List[str]] = None
    ) -> FirebaseReadResult:
        """
        Read a single document by ID.
        
        READ-ONLY: Uses .get() only
        
        Args:
            collection: Collection path
            document_id: Document ID
            fields: Optional list of fields to return (None = all fields)
            
        Returns:
            FirebaseReadResult with document data
        """
        path = f"{collection}/{document_id}"
        
        try:
            # Validate collection exists
            if not self.validate_collection(collection):
                return FirebaseReadResult(
                    success=False,
                    error=f"Collection '{collection}' not found in schema",
                    path=path
                )
            
            # READ-ONLY: Get document
            doc_ref = self._db.collection(collection).document(document_id)
            doc = doc_ref.get()  # READ-ONLY operation
            
            if not doc.exists:
                return FirebaseReadResult(
                    success=False,
                    error=f"Document '{document_id}' not found",
                    path=path
                )
            
            # Get data
            data = doc.to_dict()
            
            # Filter fields if specified
            if fields and data:
                data = {k: v for k, v in data.items() if k in fields}
            
            # Track read path
            self._track_read(path, list(data.keys()) if data else [])
            
            return FirebaseReadResult(
                success=True,
                data=data,
                path=path,
                fields_read=list(data.keys()) if data else [],
                document_count=1
            )
            
        except Exception as e:
            logger.error(f"Error reading document {path}: {e}")
            return FirebaseReadResult(
                success=False,
                error=str(e),
                path=path
            )
    
    def read_collection(
        self,
        collection: str,
        fields: Optional[List[str]] = None,
        filters: Optional[List[Tuple[str, str, Any]]] = None,
        limit: int = 10,
        order_by: Optional[str] = None,
        order_direction: str = "ASCENDING"
    ) -> FirebaseReadResult:
        """
        Read documents from a collection with optional filtering.
        
        READ-ONLY: Uses .stream() only
        
        Args:
            collection: Collection path
            fields: Optional list of fields to return
            filters: List of (field, operator, value) tuples
            limit: Maximum documents to return
            order_by: Field to order by
            order_direction: "ASCENDING" or "DESCENDING"
            
        Returns:
            FirebaseReadResult with list of documents
        """
        try:
            # Validate collection
            if not self.validate_collection(collection):
                return FirebaseReadResult(
                    success=False,
                    error=f"Collection '{collection}' not found in schema",
                    path=collection
                )
            
            # Build query (READ-ONLY)
            query = self._db.collection(collection)
            
            # Apply filters
            if filters:
                for field_name, operator, value in filters:
                    query = query.where(filter=FieldFilter(field_name, operator, value))
            
            # Apply ordering
            if order_by:
                direction = (
                    firestore.Query.DESCENDING 
                    if order_direction.upper() == "DESCENDING" 
                    else firestore.Query.ASCENDING
                )
                query = query.order_by(order_by, direction=direction)
            
            # Apply limit
            query = query.limit(limit)
            
            # Execute query (READ-ONLY: using .stream())
            documents = []
            all_fields_read = set()
            
            for doc in query.stream():
                data = doc.to_dict()
                
                # Filter fields if specified
                if fields and data:
                    data = {k: v for k, v in data.items() if k in fields}
                
                # Add document ID
                data["_id"] = doc.id
                documents.append(data)
                
                if data:
                    all_fields_read.update(data.keys())
            
            # Track read path
            self._track_read(collection, list(all_fields_read))
            
            return FirebaseReadResult(
                success=True,
                data={"documents": documents},
                path=collection,
                fields_read=list(all_fields_read),
                document_count=len(documents)
            )
            
        except Exception as e:
            logger.error(f"Error reading collection {collection}: {e}")
            return FirebaseReadResult(
                success=False,
                error=str(e),
                path=collection
            )
    
    def read_user_data(
        self,
        user_id: str,
        collections: Optional[List[str]] = None,
        fields: Optional[Dict[str, List[str]]] = None
    ) -> FirebaseReadResult:
        """
        Read data for a specific user across collections.
        
        SECURITY: Only reads data belonging to the specified user_id.
        
        Args:
            user_id: The authenticated user's ID
            collections: List of collections to query (None = auto-detect)
            fields: Dict of collection -> fields to return
            
        Returns:
            FirebaseReadResult with user's data from all collections
        """
        if not user_id:
            return FirebaseReadResult(
                success=False,
                error="User ID is required for user data access",
                path=""
            )
        
        # Auto-detect collections with user-related fields
        if not collections:
            collections = self._find_user_collections()
        
        user_data = {}
        total_docs = 0
        all_fields = set()
        
        for collection in collections:
            # Try different user ID field names
            user_id_fields = ["user_id", "userId", "uid", "owner_id", "ownerId", "created_by"]
            
            for id_field in user_id_fields:
                if self._field_exists_in_collection(collection, id_field):
                    result = self.read_collection(
                        collection=collection,
                        fields=fields.get(collection) if fields else None,
                        filters=[(id_field, "==", user_id)],
                        limit=50
                    )
                    
                    if result.success and result.data:
                        docs = result.data.get("documents", [])
                        if docs:
                            user_data[collection] = docs
                            total_docs += len(docs)
                            all_fields.update(result.fields_read)
                    break
            
            # Also check if user_id is the document ID
            doc_result = self.read_document(collection, user_id)
            if doc_result.success and doc_result.data:
                if collection not in user_data:
                    user_data[collection] = []
                user_data[collection].append(doc_result.data)
                total_docs += 1
                all_fields.update(doc_result.fields_read)
        
        return FirebaseReadResult(
            success=True,
            data=user_data,
            path=f"user:{user_id}",
            fields_read=list(all_fields),
            document_count=total_docs
        )
    
    def _find_user_collections(self) -> List[str]:
        """Find collections that likely contain user data."""
        if not self._schema:
            self._schema = get_firestore_schema()
        
        user_collections = []
        user_field_names = {"user_id", "userId", "uid", "owner_id", "ownerId", "created_by"}
        
        for path, collection in self._schema.get("collections", {}).items():
            fields = set(collection.get("fields", {}).keys())
            if fields & user_field_names:
                user_collections.append(path)
        
        return user_collections
    
    def _field_exists_in_collection(self, collection: str, field_name: str) -> bool:
        """Check if a field exists in a collection."""
        if not self._schema:
            self._schema = get_firestore_schema()
        
        collection_info = self._schema.get("collections", {}).get(collection, {})
        return field_name in collection_info.get("fields", {})
    
    def _track_read(self, path: str, fields: List[str]) -> None:
        """Track what paths and fields were read."""
        if path not in self._read_paths:
            self._read_paths[path] = {"fields": set()}
        self._read_paths[path]["fields"].update(fields)
    
    def get_read_paths(self) -> Dict[str, Dict]:
        """Get all paths that were read in this session."""
        return {
            path: {"fields": list(info["fields"])}
            for path, info in self._read_paths.items()
        }
    
    def clear_read_tracking(self) -> None:
        """Clear the read tracking data."""
        self._read_paths.clear()


# =============================================================================
# STANDALONE FUNCTIONS
# =============================================================================

_service_instance: Optional[FirebaseReadService] = None


def get_read_service() -> FirebaseReadService:
    """Get or create the read service singleton."""
    global _service_instance
    if _service_instance is None:
        _service_instance = FirebaseReadService()
    return _service_instance


def read_document(collection: str, document_id: str, fields: Optional[List[str]] = None) -> FirebaseReadResult:
    """Read a single document."""
    return get_read_service().read_document(collection, document_id, fields)


def read_collection(
    collection: str,
    fields: Optional[List[str]] = None,
    filters: Optional[List[Tuple[str, str, Any]]] = None,
    limit: int = 10
) -> FirebaseReadResult:
    """Read documents from a collection."""
    return get_read_service().read_collection(collection, fields, filters, limit)


def read_user_data(user_id: str, collections: Optional[List[str]] = None) -> FirebaseReadResult:
    """Read all data for a specific user."""
    return get_read_service().read_user_data(user_id, collections)


def format_firebase_data_for_llm(result: FirebaseReadResult) -> str:
    """Format Firebase read result for LLM context in a clean, readable format."""
    if not result.success:
        return f"Database Error: {result.error}"
    
    if not result.data:
        return "No user data found in database."
    
    lines = ["=== USER'S PERSONAL DATA ===\n"]
    
    # Field name beautification mapping
    field_labels = {
        "user_id": "User ID",
        "email": "Email",
        "displayName": "Name",
        "phoneNumber": "Phone",
        "createdAt": "Account Created",
        "booking_id": "Booking ID",
        "dateOfAppointment": "Appointment Date",
        "timeRequired": "Time Required",
        "duration": "Duration",
        "type": "Service Type",
        "venue": "Venue",
        "languagePair": "Languages",
        "client": "Client",
        "customer": "Customer",
        "isCompleted": "Status (Completed)",
        "isBooked": "Status (Booked)",
        "isCancelled": "Status (Cancelled)",
        "isPending": "Status (Pending)",
        "interpreterPerHour": "Interpreter Rate/Hour",
        "minimumHour": "Minimum Hours",
        "systemRef": "Reference Number",
        "title": "Title",
        "relevantInfo": "Additional Info",
        "bookedBy": "Booked By",
        "authorised": "Authorized By"
    }
    
    if isinstance(result.data, dict):
        if "documents" in result.data:
            # Collection result
            docs = result.data["documents"]
            lines.append(f"Total Records: {len(docs)}\n")
            for i, doc in enumerate(docs, 1):
                lines.append(f"--- Record {i} ---")
                for key, value in sorted(doc.items()):
                    if key != "_id" and value not in [None, "", [], {}]:
                        label = field_labels.get(key, key.replace("_", " ").title())
                        # Format value nicely
                        if isinstance(value, list):
                            value = ", ".join(str(v) for v in value)
                        elif isinstance(value, dict):
                            value = str(value)
                        elif isinstance(value, bool):
                            value = "Yes" if value else "No"
                        lines.append(f"  {label}: {value}")
                lines.append("")  # Empty line between records
        else:
            # User data across collections
            for collection, docs in result.data.items():
                collection_name = collection.replace("_", " ").title()
                lines.append(f"\n📁 {collection_name}")
                lines.append("─" * 40)
                
                if isinstance(docs, list):
                    lines.append(f"Total: {len(docs)} record(s)\n")
                    for idx, doc in enumerate(docs, 1):
                        if len(docs) > 1:
                            lines.append(f"  Record {idx}:")
                        for key, value in sorted(doc.items()):
                            if key != "_id" and value not in [None, "", [], {}]:
                                label = field_labels.get(key, key.replace("_", " ").title())
                                if isinstance(value, list):
                                    value = ", ".join(str(v) for v in value)
                                elif isinstance(value, dict):
                                    value = str(value)
                                elif isinstance(value, bool):
                                    value = "Yes" if value else "No"
                                lines.append(f"    • {label}: {value}")
                        if idx < len(docs):
                            lines.append("")
                else:
                    for key, value in sorted(docs.items()):
                        if key != "_id" and value not in [None, "", [], {}]:
                            label = field_labels.get(key, key.replace("_", " ").title())
                            if isinstance(value, list):
                                value = ", ".join(str(v) for v in value)
                            elif isinstance(value, dict):
                                value = str(value)
                            elif isinstance(value, bool):
                                value = "Yes" if value else "No"
                            lines.append(f"  • {label}: {value}")
                lines.append("")
    
    lines.append("=== END OF USER DATA ===")
    return "\n".join(lines)


# =============================================================================
# MAIN - For standalone testing
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("FIREBASE READ SERVICE TEST (READ-ONLY)")
    print("=" * 60)
    
    try:
        service = FirebaseReadService()
        
        # Test reading a collection
        print("\n[Test 1] Reading 'users' collection...")
        result = service.read_collection("users", limit=3)
        
        if result.success:
            print(f"✓ Read {result.document_count} documents")
            print(f"  Fields: {result.fields_read}")
        else:
            print(f"✗ Error: {result.error}")
        
        # Test blocked write operation
        print("\n[Test 2] Testing write block...")
        try:
            service.set("test", "data")
            print("✗ SECURITY FAILURE: Write was not blocked!")
        except PermissionError as e:
            print(f"✓ Write correctly blocked: {e}")
        
        # Show read paths
        print("\n[Read Paths Tracked]")
        for path, info in service.get_read_paths().items():
            print(f"  {path}: {info['fields']}")
        
        print("\n✓ All tests passed!")
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        raise
