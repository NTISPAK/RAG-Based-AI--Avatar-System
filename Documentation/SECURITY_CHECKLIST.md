# 🔒 Security Checklist - Before Pushing to GitHub

## ✅ Pre-Push Security Verification

Run through this checklist **BEFORE** pushing to GitHub:

### 1. Environment Variables ✅

- [x] `.env` file exists locally (for your use)
- [x] `.env` is listed in `.gitignore`
- [x] `.env.example` exists (template for others)
- [x] `.env.example` has NO real API keys

**Verify:**
```bash
# This should show .env is ignored
git status | grep .env

# If .env appears, it's NOT being ignored - FIX IMMEDIATELY
```

### 2. API Keys ✅

- [x] No API keys in code files
- [x] No API keys in README
- [x] No API keys in comments
- [x] All keys loaded from environment variables

**Check these files:**
```bash
# Should return nothing (no hardcoded keys)
grep -r "AIza" *.py *.md
grep -r "api_key.*=" *.py | grep -v "os.getenv"
```

### 3. Git Ignore ✅

- [x] `.gitignore` file exists
- [x] `.gitignore` includes `.env`
- [x] `.gitignore` includes `.venv/`
- [x] `.gitignore` includes `__pycache__/`

**Verify .gitignore contents:**
```bash
cat .gitignore | grep -E "\.env|\.venv|__pycache__"
```

### 4. Sensitive Files ✅

These should **NEVER** be in Git:

- [ ] ❌ `.env` 
- [ ] ❌ `.venv/`
- [ ] ❌ `__pycache__/`
- [ ] ❌ `*.pyc`
- [ ] ❌ Firebase service account JSON
- [ ] ❌ Database files
- [ ] ❌ Log files with sensitive data

**Verify:**
```bash
git status
# None of the above should appear
```

### 5. Code Review ✅

Check these files manually:

- [ ] `main.py` - No hardcoded secrets
- [ ] `ingest.py` - No hardcoded secrets
- [ ] `.env.example` - Only placeholder values
- [ ] `README.md` - No real API keys

---

## 🚨 What to Do If You Find Issues

### Issue: .env is not being ignored

**Fix:**
```bash
# Add to .gitignore
echo ".env" >> .gitignore

# Remove from Git if already added
git rm --cached .env

# Commit
git add .gitignore
git commit -m "Fix: Ignore .env file"
```

### Issue: API key is hardcoded in code

**Fix:**
```python
# ❌ BAD
GOOGLE_API_KEY = "AIzaSyBVipvYccz9t4Y33H8VPvHF1r2Dlx0Wziw"

# ✅ GOOD
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
```

### Issue: Accidentally committed .env

**Fix:**
```bash
# Remove from Git history
git rm --cached .env
git commit -m "Remove .env from repository"

# IMPORTANT: Revoke the exposed API key
# Generate new key from https://aistudio.google.com
# Update your local .env with new key
```

---

## ✅ Final Verification Before Push

Run these commands:

```bash
# 1. Check what will be committed
git status

# 2. Verify .env is NOT listed
git status | grep -q "\.env" && echo "⚠️ WARNING: .env will be committed!" || echo "✅ .env is ignored"

# 3. Check for API keys in staged files
git diff --cached | grep -i "api.*key" && echo "⚠️ WARNING: Possible API key found!" || echo "✅ No API keys detected"

# 4. List all files to be committed
git ls-files
```

**Expected output:**
- ✅ `.env` should NOT appear
- ✅ `.venv/` should NOT appear
- ✅ No API keys in diff

---

## 🎯 Safe to Push Checklist

Before running `git push`, confirm:

- [ ] `.env` is in `.gitignore`
- [ ] `.env` does NOT appear in `git status`
- [ ] `.env.example` has placeholder values only
- [ ] No API keys in any `.py` files
- [ ] No API keys in `README.md`
- [ ] All secrets loaded via `os.getenv()`
- [ ] Reviewed `git status` output
- [ ] Reviewed `git diff --cached` output

**If ALL boxes are checked:** ✅ **SAFE TO PUSH**

---

## 📋 Post-Push Verification

After pushing to GitHub:

1. **Visit your GitHub repository**
2. **Click on files and verify:**
   - ✅ `.gitignore` is present
   - ✅ `.env.example` is present
   - ❌ `.env` is NOT present
   - ❌ No API keys visible in any file

3. **Search repository for API keys:**
   - Go to your repo on GitHub
   - Press `t` to open file finder
   - Search for `AIza` or `api_key`
   - Should find ZERO results

---

## 🔐 Environment Variables in Production

When deploying to production:

### Option 1: Platform Environment Variables

**Heroku:**
```bash
heroku config:set GOOGLE_API_KEY=your_key
```

**Vercel:**
```bash
vercel env add GOOGLE_API_KEY
```

**Railway:**
```bash
railway variables set GOOGLE_API_KEY=your_key
```

### Option 2: Secrets Manager

**AWS:**
- Use AWS Secrets Manager
- Reference in code via boto3

**Azure:**
- Use Azure Key Vault
- Reference via Azure SDK

**Google Cloud:**
- Use Secret Manager
- Reference via Google Cloud SDK

---

## 🚨 Emergency: API Key Exposed

If you accidentally pushed an API key:

### Immediate Actions (Within 5 minutes)

1. **Revoke the key immediately**
   - Go to https://aistudio.google.com
   - Delete the exposed API key

2. **Generate new key**
   - Create a new API key
   - Update your local `.env`

3. **Remove from Git history**
   ```bash
   # Remove .env from all commits
   git filter-branch --force --index-filter \
     "git rm --cached --ignore-unmatch .env" \
     --prune-empty --tag-name-filter cat -- --all
   
   # Force push (WARNING: Rewrites history)
   git push origin --force --all
   ```

4. **Notify your team**
   - If this is a team project
   - Everyone needs to re-clone

### Long-term Actions

1. Enable GitHub secret scanning
2. Use pre-commit hooks
3. Implement automated security checks
4. Regular security audits

---

## 🛡️ Prevention Tools

### Pre-commit Hook

Create `.git/hooks/pre-commit`:
```bash
#!/bin/bash

# Check for .env in staged files
if git diff --cached --name-only | grep -q "^\.env$"; then
    echo "❌ ERROR: Attempting to commit .env file!"
    echo "Remove .env from staging: git reset HEAD .env"
    exit 1
fi

# Check for API keys
if git diff --cached | grep -iE "AIza|api.*key.*=.*['\"]"; then
    echo "⚠️  WARNING: Possible API key detected!"
    echo "Review your changes before committing."
    exit 1
fi

echo "✅ Pre-commit checks passed"
exit 0
```

Make executable:
```bash
chmod +x .git/hooks/pre-commit
```

---

## ✅ You're Secure!

If you've completed this checklist:
- ✅ Your API keys are safe
- ✅ Your code is ready for GitHub
- ✅ Other developers can clone and run
- ✅ No sensitive data exposed

**Happy coding! 🚀**
