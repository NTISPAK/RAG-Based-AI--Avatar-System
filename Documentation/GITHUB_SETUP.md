# GitHub Setup Guide

## 🔒 Secure Your Code Before Pushing to GitHub

Follow these steps to safely push your code to GitHub without exposing sensitive information.

---

## ✅ Pre-Push Checklist

### 1. Verify .gitignore is Working

```bash
# Check what will be committed
git status

# Make sure these are NOT listed:
# ❌ .env
# ❌ .venv/
# ❌ __pycache__/
# ❌ *.pyc
```

### 2. Remove Sensitive Data from .env

Your `.env` file should **NEVER** be committed. It's already in `.gitignore`.

**Current .env (LOCAL ONLY - NOT IN GIT):**
```env
GOOGLE_API_KEY=AIzaSyBVipvYccz9t4Y33H8VPvHF1r2Dlx0Wziw
QDRANT_URL=http://localhost:6333
COLLECTION_NAME=policy_docs
```

**What's in GitHub (.env.example):**
```env
GOOGLE_API_KEY=your_gemini_api_key_here
QDRANT_URL=http://localhost:6333
COLLECTION_NAME=policy_docs
```

### 3. Verify .gitignore Exists

Check that `.gitignore` contains:
```
.env
.env.local
.venv/
__pycache__/
*.pyc
```

---

## 🚀 Push to GitHub

### Step 1: Initialize Git Repository

```bash
cd /Users/naumanrashid/Desktop/Tester
git init
```

### Step 2: Add Files

```bash
# Add all files (sensitive ones are excluded by .gitignore)
git add .

# Verify .env is NOT staged
git status
# Should NOT see .env in the list
```

### Step 3: Create First Commit

```bash
git commit -m "Initial commit: NTIS Policy RAG Chatbot"
```

### Step 4: Create GitHub Repository

1. Go to https://github.com/new
2. Repository name: `ntis-policy-chatbot` (or your choice)
3. Description: "RAG chatbot for NTIS policy questions"
4. Choose **Public** or **Private**
5. **DO NOT** initialize with README (we already have one)
6. Click "Create repository"

### Step 5: Link and Push

```bash
# Add remote (replace with your GitHub username)
git remote add origin https://github.com/YOUR_USERNAME/ntis-policy-chatbot.git

# Push to GitHub
git branch -M main
git push -u origin main
```

---

## 🔐 Security Verification

### Check What's on GitHub

After pushing, verify on GitHub that these files are **NOT** present:
- ❌ `.env`
- ❌ `.venv/`
- ❌ `__pycache__/`
- ❌ Any file with API keys

### Check What IS on GitHub

These files **SHOULD** be present:
- ✅ `.gitignore`
- ✅ `.env.example`
- ✅ `README.md`
- ✅ `main.py`
- ✅ `ingest.py`
- ✅ `requirements.txt`
- ✅ `templates/index.html`
- ✅ `static/style.css`
- ✅ Documentation files

---

## 👥 For Other Developers (Setup Instructions)

When someone clones your repository:

### 1. Clone Repository
```bash
git clone https://github.com/YOUR_USERNAME/ntis-policy-chatbot.git
cd ntis-policy-chatbot
```

### 2. Create .env from Template
```bash
cp .env.example .env
```

### 3. Edit .env with Their Own Keys
```bash
# They need to add their own API key
nano .env  # or use any text editor
```

### 4. Install and Run
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python ingest.py
uvicorn main:app --reload --port 8080
```

---

## 🛡️ If You Accidentally Committed .env

### Remove from Git History

```bash
# Remove .env from Git (keeps local file)
git rm --cached .env

# Commit the removal
git commit -m "Remove .env from Git"

# Push
git push origin main
```

### If API Key Was Exposed

1. **Immediately revoke** the exposed API key
2. Generate a new key from [Google AI Studio](https://aistudio.google.com)
3. Update your local `.env` with new key
4. Never commit the new key

---

## 📋 GitHub Repository Settings

### Add Repository Description

Go to repository settings and add:
```
A RAG chatbot for NTIS policy questions using Qdrant, LangChain, and Google Gemini
```

### Add Topics (Tags)

Add these topics to help others find your project:
- `rag`
- `chatbot`
- `langchain`
- `qdrant`
- `gemini`
- `fastapi`
- `python`
- `vector-database`
- `semantic-search`

### Add README Badges

Already included in README.md:
- Python version
- FastAPI version
- License

---

## 🔄 Future Updates

### Making Changes

```bash
# Make your changes
git add .
git commit -m "Description of changes"
git push origin main
```

### Pulling Changes (if working from multiple machines)

```bash
git pull origin main
```

---

## 🚨 Important Reminders

1. **NEVER** commit `.env` file
2. **ALWAYS** use `.env.example` as template
3. **ROTATE** API keys if exposed
4. **CHECK** `git status` before committing
5. **VERIFY** GitHub repository after first push

---

## ✅ Your Repository is Now Secure!

Your code is on GitHub with:
- ✅ No API keys exposed
- ✅ No sensitive URLs
- ✅ Clear setup instructions for others
- ✅ Professional documentation
- ✅ Easy to clone and run

**Your local system still works** because:
- Your `.env` file is still on your computer
- It's just not tracked by Git
- You can continue using the app normally

---

## 📞 Need Help?

If you accidentally exposed secrets:
1. Revoke the API key immediately
2. Generate new key
3. Update local `.env`
4. Consider using GitHub's secret scanning alerts
