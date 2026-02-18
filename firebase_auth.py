"""
Firebase Authentication Module
===============================
Handles user authentication and token verification.
Ensures only authenticated users can access their own data.

SECURITY:
- Verifies Firebase ID tokens
- Extracts authenticated user UID
- Blocks access without valid token
"""

import logging
from typing import Optional, Dict, Any
from fastapi import HTTPException, Header, Depends
from firebase_admin import auth

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AuthenticatedUser:
    """Represents an authenticated user."""
    
    def __init__(self, uid: str, email: Optional[str] = None, name: Optional[str] = None):
        self.uid = uid
        self.email = email
        self.name = name
    
    def __repr__(self):
        return f"AuthenticatedUser(uid={self.uid}, email={self.email})"


async def verify_firebase_token(authorization: Optional[str] = Header(None)) -> Optional[AuthenticatedUser]:
    """
    Verify Firebase ID token from Authorization header.
    
    Args:
        authorization: Authorization header (format: "Bearer <token>")
        
    Returns:
        AuthenticatedUser if token is valid, None otherwise
        
    Raises:
        HTTPException: If token is invalid or expired
    """
    if not authorization:
        return None
    
    # Extract token from "Bearer <token>"
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=401,
            detail="Invalid authorization header format. Expected: 'Bearer <token>'"
        )
    
    token = parts[1]
    
    try:
        # Verify the ID token with Firebase Admin SDK
        decoded_token = auth.verify_id_token(token)
        
        # Extract user information
        uid = decoded_token.get("uid")
        email = decoded_token.get("email")
        name = decoded_token.get("name")
        
        if not uid:
            raise HTTPException(
                status_code=401,
                detail="Invalid token: missing user ID"
            )
        
        logger.info(f"[Auth] User authenticated: {uid} ({email})")
        
        return AuthenticatedUser(uid=uid, email=email, name=name)
        
    except auth.InvalidIdTokenError as e:
        logger.warning(f"[Auth] Invalid token: {e}")
        raise HTTPException(
            status_code=401,
            detail=f"Invalid or expired token: {str(e)}"
        )
    except auth.ExpiredIdTokenError as e:
        logger.warning(f"[Auth] Expired token: {e}")
        raise HTTPException(
            status_code=401,
            detail="Token has expired. Please log in again."
        )
    except Exception as e:
        logger.error(f"[Auth] Token verification error: {e}")
        raise HTTPException(
            status_code=401,
            detail=f"Authentication failed: {str(e)}"
        )


async def require_auth(user: Optional[AuthenticatedUser] = Depends(verify_firebase_token)) -> AuthenticatedUser:
    """
    Dependency that requires authentication.
    
    Use this for endpoints that MUST have an authenticated user.
    
    Args:
        user: Authenticated user from token verification
        
    Returns:
        AuthenticatedUser
        
    Raises:
        HTTPException: If user is not authenticated
    """
    if user is None:
        raise HTTPException(
            status_code=401,
            detail="Authentication required. Please log in."
        )
    
    return user


async def optional_auth(user: Optional[AuthenticatedUser] = Depends(verify_firebase_token)) -> Optional[AuthenticatedUser]:
    """
    Dependency that allows optional authentication.
    
    Use this for endpoints that work with or without authentication,
    but provide enhanced features for authenticated users.
    
    Args:
        user: Authenticated user from token verification (may be None)
        
    Returns:
        AuthenticatedUser or None
    """
    return user


def get_user_id_from_token(authorization: Optional[str]) -> Optional[str]:
    """
    Extract user ID from authorization token without raising exceptions.
    
    Args:
        authorization: Authorization header string
        
    Returns:
        User ID if token is valid, None otherwise
    """
    if not authorization:
        return None
    
    try:
        parts = authorization.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            return None
        
        token = parts[1]
        decoded_token = auth.verify_id_token(token)
        return decoded_token.get("uid")
        
    except Exception as e:
        logger.debug(f"[Auth] Token extraction failed: {e}")
        return None


# =============================================================================
# TESTING UTILITIES
# =============================================================================

def create_custom_token(uid: str) -> str:
    """
    Create a custom token for testing purposes.
    
    WARNING: Only use this for development/testing!
    
    Args:
        uid: User ID to create token for
        
    Returns:
        Custom token string
    """
    try:
        custom_token = auth.create_custom_token(uid)
        return custom_token.decode('utf-8')
    except Exception as e:
        logger.error(f"[Auth] Failed to create custom token: {e}")
        raise


def verify_token_info(token: str) -> Dict[str, Any]:
    """
    Get information about a token without raising exceptions.
    
    Args:
        token: ID token to verify
        
    Returns:
        Dictionary with token information or error details
    """
    try:
        decoded = auth.verify_id_token(token)
        return {
            "valid": True,
            "uid": decoded.get("uid"),
            "email": decoded.get("email"),
            "name": decoded.get("name"),
            "exp": decoded.get("exp"),
            "iat": decoded.get("iat")
        }
    except auth.ExpiredIdTokenError:
        return {"valid": False, "error": "Token expired"}
    except auth.InvalidIdTokenError as e:
        return {"valid": False, "error": f"Invalid token: {str(e)}"}
    except Exception as e:
        return {"valid": False, "error": f"Verification failed: {str(e)}"}


# =============================================================================
# MAIN - For standalone testing
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("FIREBASE AUTHENTICATION MODULE TEST")
    print("=" * 60)
    
    # Initialize Firebase (if not already done)
    import firebase_admin
    from firebase_admin import credentials
    import os
    
    if not firebase_admin._apps:
        cred_path = os.getenv("FIREBASE_CREDENTIALS_PATH", "./ntis-pro-firebase-adminsdk-y74ok-3f7652312c.json")
        cred = credentials.Certificate(cred_path)
        firebase_admin.initialize_app(cred)
        print(f"✓ Firebase initialized from: {cred_path}")
    
    # Test: Create a custom token for testing
    test_uid = "test_user_123"
    print(f"\n[Test] Creating custom token for UID: {test_uid}")
    
    try:
        custom_token = create_custom_token(test_uid)
        print(f"✓ Custom token created: {custom_token[:50]}...")
        
        # Note: Custom tokens need to be exchanged for ID tokens via Firebase Auth REST API
        print("\nℹ To test authentication:")
        print("1. Use Firebase Web SDK to sign in with the custom token")
        print("2. Get the ID token with: firebase.auth().currentUser.getIdToken()")
        print("3. Use that ID token in the Authorization header")
        
    except Exception as e:
        print(f"✗ Error: {e}")
    
    print("\n" + "=" * 60)
