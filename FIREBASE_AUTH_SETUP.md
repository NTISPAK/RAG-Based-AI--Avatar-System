# Firebase Authentication Setup Guide

## 🔐 Overview

This guide will help you set up Firebase Authentication so that only logged-in users can access their own data from Firestore.

## ✅ What You Need

1. **Firebase Project** (you already have: `ntis-pro`)
2. **Firebase Admin SDK credentials** (you already have)
3. **Firebase Web SDK configuration** (need to get)
4. **Enable Firebase Authentication** (need to do)

---

## 📋 Step-by-Step Setup

### Step 1: Get Firebase Web SDK Configuration

1. Go to [Firebase Console](https://console.firebase.google.com/)
2. Select your project: **ntis-pro**
3. Click the gear icon ⚙️ → **Project settings**
4. Scroll down to **Your apps** section
5. If you don't have a web app:
   - Click **Add app** → Select **Web** (</>) icon
   - Register app name: "NTIS Policy Assistant"
   - Click **Register app**
6. You'll see the Firebase configuration object:

```javascript
const firebaseConfig = {
  apiKey: "AIza...",
  authDomain: "ntis-pro.firebaseapp.com",
  projectId: "ntis-pro",
  storageBucket: "ntis-pro.appspot.com",
  messagingSenderId: "123456789",
  appId: "1:123456789:web:abc123"
};
```

7. **Copy these values** - you'll need them!

### Step 2: Enable Firebase Authentication

1. In Firebase Console, go to **Authentication** (left sidebar)
2. Click **Get started** (if first time)
3. Go to **Sign-in method** tab
4. Enable the authentication methods you want:

#### Option A: Email/Password (Recommended for testing)
- Click **Email/Password**
- Toggle **Enable**
- Click **Save**

#### Option B: Google Sign-In (Recommended for production)
- Click **Google**
- Toggle **Enable**
- Enter support email
- Click **Save**

### Step 3: Create Test Users

1. Go to **Authentication** → **Users** tab
2. Click **Add user**
3. Enter:
   - **Email**: test@example.com
   - **Password**: TestPassword123!
4. Click **Add user**

Repeat for any additional test users.

### Step 4: Configure Your Application

#### A. Update `.env` file

Add these lines to your `.env` file (replace with your actual values):

```env
# Firebase Web SDK Configuration
FIREBASE_API_KEY=AIzaSy...
FIREBASE_AUTH_DOMAIN=ntis-pro.firebaseapp.com
FIREBASE_PROJECT_ID=ntis-pro
FIREBASE_STORAGE_BUCKET=ntis-pro.appspot.com
FIREBASE_MESSAGING_SENDER_ID=123456789
FIREBASE_APP_ID=1:123456789:web:abc123
```

#### B. Update Frontend HTML

Replace the Firebase config in `templates/index_with_auth.html` (line ~200):

```javascript
const firebaseConfig = {
    apiKey: "YOUR_ACTUAL_API_KEY",
    authDomain: "ntis-pro.firebaseapp.com",
    projectId: "ntis-pro",
    storageBucket: "ntis-pro.appspot.com",
    messagingSenderId: "YOUR_ACTUAL_SENDER_ID",
    appId: "YOUR_ACTUAL_APP_ID"
};
```

### Step 5: Switch to Authenticated Version

Rename the files:

```bash
cd /Users/naumanrashid/Desktop/Tester/templates

# Backup current version
mv index.html index_no_auth.html

# Use authenticated version
mv index_with_auth.html index.html
```

Or manually replace the content of `index.html` with `index_with_auth.html`.

### Step 6: Restart Server

```bash
# Stop current server (Ctrl+C)

# Start with authentication
uvicorn main:app --reload --port 8080
```

---

## 🧪 Testing Authentication

### Test 1: Guest Access (Policy Questions Only)

1. Open http://localhost:8080
2. **Don't log in**
3. Ask: "What is the refund policy?"
4. ✅ Should work - returns policy information

### Test 2: Personal Data Without Login

1. Still as guest
2. Ask: "Show me my bookings"
3. ✅ Should return: "Authentication Required - Please log in..."

### Test 3: Login and Access Personal Data

1. Click **Sign In** button
2. Enter test credentials:
   - Email: test@example.com
   - Password: TestPassword123!
3. Click **Sign In**
4. ✅ Should see your profile in sidebar
5. Ask: "Show me my bookings"
6. ✅ Should return data from Firestore (if user has bookings)

### Test 4: Data Isolation

1. Log in as User A
2. Ask: "Show me my bookings"
3. Note the bookings returned
4. Log out
5. Log in as User B (different account)
6. Ask: "Show me my bookings"
7. ✅ Should see DIFFERENT bookings (User B's data only)

---

## 🔒 Security Features

### ✅ What's Protected

1. **Token Verification**
   - Every request with personal data requires valid Firebase ID token
   - Tokens are verified server-side using Firebase Admin SDK
   - Expired/invalid tokens are rejected

2. **User Data Isolation**
   - Backend ONLY queries Firestore using authenticated user's UID
   - No way to access other users' data
   - User ID comes from verified token, not request body

3. **Read-Only Access**
   - All Firestore operations are READ-ONLY
   - Write operations are blocked at code level
   - Raises `PermissionError` if attempted

### ✅ Authentication Flow

```
User Login → Firebase Auth → ID Token
    ↓
Request with Token → Backend verifies token → Extract UID
    ↓
Query Firestore with UID filter → Return ONLY user's data
    ↓
LLM generates response → Return to user
```

---

## 📊 API Endpoints

### `/chat` - Main Chat Endpoint

**Without Authentication:**
```bash
curl -X POST http://localhost:8080/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What is the refund policy?"}'
```

**With Authentication:**
```bash
curl -X POST http://localhost:8080/chat \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ID_TOKEN" \
  -d '{"message": "Show me my bookings"}'
```

### Response Format

```json
{
  "used_firebase": true,
  "firebase_read_paths": {
    "bookings": {"fields": ["booking_id", "status"]}
  },
  "rag_answer": "You have 3 bookings...",
  "intent": "personal_data",
  "confidence": 1.0
}
```

---

## 🐛 Troubleshooting

### Issue: "Authentication Required" even after login

**Solution:**
1. Check browser console for errors
2. Verify Firebase config is correct in HTML
3. Check that ID token is being sent in Authorization header
4. Try logging out and back in

### Issue: "Invalid token" error

**Solution:**
1. Token may have expired (tokens expire after 1 hour)
2. Log out and log back in to get fresh token
3. Check that Firebase Admin SDK credentials match the project

### Issue: Can't see personal data after login

**Solution:**
1. Check that user exists in Firestore
2. Verify Firestore documents have `user_id` or `uid` field
3. Check server logs for Firebase query results
4. Ensure user_id in Firestore matches Firebase Auth UID

### Issue: Seeing other users' data

**Solution:**
1. **CRITICAL SECURITY ISSUE** - Report immediately
2. Check that backend is using `current_user.uid` from token
3. Verify Firestore queries include user_id filter
4. Review `firebase_read_service.py` for proper filtering

---

## 📝 User Management

### Add New Users

**Via Firebase Console:**
1. Go to Authentication → Users
2. Click **Add user**
3. Enter email and password
4. Click **Add user**

**Via Code (for bulk import):**
```python
from firebase_admin import auth

# Create user
user = auth.create_user(
    email='newuser@example.com',
    password='SecurePassword123!',
    display_name='New User'
)
print(f'Created user: {user.uid}')
```

### Reset Password

1. Go to Authentication → Users
2. Find user
3. Click three dots → **Reset password**
4. User will receive password reset email

---

## 🚀 Production Checklist

Before deploying to production:

- [ ] Enable Google Sign-In (easier for users)
- [ ] Set up email verification
- [ ] Configure password reset emails
- [ ] Add rate limiting to prevent abuse
- [ ] Set up Firebase Security Rules for Firestore
- [ ] Enable Firebase App Check for additional security
- [ ] Monitor authentication logs
- [ ] Set up user roles/permissions if needed
- [ ] Add session management
- [ ] Implement token refresh logic

---

## 📚 Additional Resources

- [Firebase Authentication Docs](https://firebase.google.com/docs/auth)
- [Firebase Admin SDK Docs](https://firebase.google.com/docs/admin/setup)
- [Firestore Security Rules](https://firebase.google.com/docs/firestore/security/get-started)
- [Firebase Best Practices](https://firebase.google.com/docs/auth/admin/verify-id-tokens)

---

## ✅ Summary

After completing this setup:

1. ✅ Users must log in to access personal data
2. ✅ Each user sees ONLY their own data
3. ✅ Policy questions work without login
4. ✅ All Firebase operations are READ-ONLY
5. ✅ Tokens are verified server-side
6. ✅ User data is isolated by UID

**Your RAG system is now secure and user-authenticated!** 🎉
