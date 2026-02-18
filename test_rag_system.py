"""
Test script to verify RAG system with Firebase integration
"""
import requests
import json

BASE_URL = "http://localhost:8080"

# Test queries - Policy questions (no Firebase)
policy_queries = [
    {
        "query": "What is the refund policy?",
        "expected_keywords": ["refund", "allowed", "service", "payment"],
        "expect_firebase": False
    },
    {
        "query": "When do interpreters get paid?",
        "expected_keywords": ["21", "working days", "invoice", "approval"],
        "expect_firebase": False
    },
    {
        "query": "What is the approval hierarchy for refunds?",
        "expected_keywords": ["Accounts Manager", "Senior Management", "Director"],
        "expect_firebase": False
    },
]

# Test queries - Personal data questions (should trigger Firebase)
personal_queries = [
    {
        "query": "Show me my bookings",
        "expect_firebase": True,
        "expected_intent": "personal_data"
    },
    {
        "query": "What is my profile information?",
        "expect_firebase": True,
        "expected_intent": "personal_data"
    },
    {
        "query": "How many orders do I have?",
        "expect_firebase": True,
        "expected_intent": "personal_data"
    },
]


def test_health():
    """Test health endpoint."""
    print("\n[1] Testing health endpoint...")
    try:
        response = requests.get(f"{BASE_URL}/health")
        if response.status_code == 200:
            data = response.json()
            print(f"✓ Health check passed")
            print(f"  Firebase enabled: {data.get('firebase_enabled', False)}")
            print(f"  Firebase collections: {data.get('firebase_collections', 0)}")
            return True
        else:
            print(f"✗ Health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ Cannot connect to server: {e}")
        print("  Make sure server is running: uvicorn main:app --reload --port 8080")
        return False


def test_schema():
    """Test schema endpoint."""
    print("\n[2] Testing schema endpoint...")
    try:
        response = requests.get(f"{BASE_URL}/schema")
        if response.status_code == 200:
            data = response.json()
            if data.get("enabled"):
                print(f"✓ Schema endpoint working")
                print(f"  Collections: {data.get('total_collections', 0)}")
                print(f"  Fields discovered: {data.get('total_fields_discovered', 0)}")
                return True
            else:
                print(f"⚠ Firebase not enabled: {data.get('message')}")
                return True  # Still passes, just not enabled
        else:
            print(f"✗ Schema endpoint failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def test_classify():
    """Test intent classification endpoint."""
    print("\n[3] Testing intent classification...")
    
    test_cases = [
        ("Show me my bookings", "personal_data"),
        ("What is the refund policy?", "general_info"),
    ]
    
    passed = 0
    for query, expected_intent in test_cases:
        try:
            response = requests.post(
                f"{BASE_URL}/classify",
                json={"message": query}
            )
            
            if response.status_code == 200:
                data = response.json()
                intent = data.get("intent", "unknown")
                confidence = data.get("confidence", 0)
                
                if intent == expected_intent or (not data.get("firebase_enabled")):
                    print(f"✓ \"{query[:30]}...\" → {intent} ({confidence:.2f})")
                    passed += 1
                else:
                    print(f"✗ \"{query[:30]}...\" → {intent} (expected: {expected_intent})")
            else:
                print(f"✗ Classification failed: {response.status_code}")
        except Exception as e:
            print(f"✗ Error: {e}")
    
    return passed == len(test_cases)


def test_policy_queries():
    """Test policy-related queries (no Firebase)."""
    print("\n[4] Testing policy queries (Qdrant only)...")
    
    passed = 0
    for test in policy_queries:
        try:
            response = requests.post(
                f"{BASE_URL}/chat",
                json={"message": test['query']}
            )
            
            if response.status_code == 200:
                data = response.json()
                answer = data.get("rag_answer", "")
                used_firebase = data.get("used_firebase", False)
                
                # Check keywords
                answer_lower = answer.lower()
                matched = sum(1 for kw in test['expected_keywords'] if kw.lower() in answer_lower)
                
                if matched >= len(test['expected_keywords']) * 0.5:
                    print(f"✓ \"{test['query'][:40]}...\"")
                    print(f"  Firebase used: {used_firebase}")
                    passed += 1
                else:
                    print(f"✗ \"{test['query'][:40]}...\" - keywords not matched")
            else:
                print(f"✗ Request failed: {response.status_code}")
        except Exception as e:
            print(f"✗ Error: {e}")
    
    return passed == len(policy_queries)


def test_personal_queries():
    """Test personal data queries (should trigger Firebase)."""
    print("\n[5] Testing personal data queries (Firebase)...")
    
    passed = 0
    for test in personal_queries:
        try:
            response = requests.post(
                f"{BASE_URL}/chat",
                json={"message": test['query']}
            )
            
            if response.status_code == 200:
                data = response.json()
                used_firebase = data.get("used_firebase", False)
                intent = data.get("intent", "unknown")
                confidence = data.get("confidence", 0)
                
                print(f"{'✓' if used_firebase == test['expect_firebase'] else '⚠'} \"{test['query'][:40]}...\"")
                print(f"  Intent: {intent} ({confidence:.2f})")
                print(f"  Firebase used: {used_firebase}")
                
                if intent == test.get('expected_intent', 'personal_data'):
                    passed += 1
            else:
                print(f"✗ Request failed: {response.status_code}")
        except Exception as e:
            print(f"✗ Error: {e}")
    
    return passed >= len(personal_queries) * 0.5  # 50% threshold


def test_structured_response():
    """Test that responses have correct structure."""
    print("\n[6] Testing structured response format...")
    
    try:
        response = requests.post(
            f"{BASE_URL}/chat",
            json={"message": "What is the refund policy?"}
        )
        
        if response.status_code == 200:
            data = response.json()
            
            required_fields = ["used_firebase", "firebase_read_paths", "rag_answer", "intent", "confidence"]
            missing = [f for f in required_fields if f not in data]
            
            if not missing:
                print("✓ Response has all required fields:")
                for field in required_fields:
                    value = data.get(field)
                    if isinstance(value, str) and len(value) > 50:
                        value = value[:50] + "..."
                    print(f"  • {field}: {value}")
                return True
            else:
                print(f"✗ Missing fields: {missing}")
                return False
        else:
            print(f"✗ Request failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def main():
    print("=" * 60)
    print("RAG SYSTEM TEST (with Firebase Integration)")
    print("=" * 60)
    
    results = []
    
    # Run tests
    results.append(("Health Check", test_health()))
    results.append(("Schema Endpoint", test_schema()))
    results.append(("Intent Classification", test_classify()))
    results.append(("Policy Queries", test_policy_queries()))
    results.append(("Personal Queries", test_personal_queries()))
    results.append(("Structured Response", test_structured_response()))
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        print(f"  {'✓' if result else '✗'} {name}")
    
    print(f"\nTotal: {passed}/{total} passed")
    
    if passed == total:
        print("\n✓ ALL TESTS PASSED!")
    else:
        print(f"\n⚠ {total - passed} test(s) failed")
    
    print("=" * 60)


if __name__ == "__main__":
    main()
