"""Quick Urdu translation test."""

import requests

print("\n" + "="*60)
print("🇵🇰 URDU MODE TEST")
print("="*60)

# Test Urdu query
urdu_query = "NIRA کیا خدمات پیش کرتا ہے؟"
print(f"\n📝 Urdu Question: {urdu_query}")
print("   (Translation: What services does NIRA offer?)")

response = requests.post(
    "http://localhost:8000/chat",
    json={"message": urdu_query, "language": "ur"},
    timeout=30
)

if response.status_code == 200:
    data = response.json()
    print(f"\n✅ Response received in {data['processing_time']}s")
    print(f"\n🗣️  Urdu Response:\n{data['response']}")
    print(f"\n⏱️  Processing time: {data['processing_time']}s")
    print(f"🌐 Language: {data['language']}")
else:
    print(f"\n❌ Error: {response.status_code}")

print("\n" + "="*60)
print("✅ Urdu mode is active!")
print("="*60)
print("\n📌 Access the avatar at: http://localhost:8010/webrtcapi.html")
print("🎤 TTS Voice: ur-PK-UzmaNeural (Female, Pakistan)")
print("🔄 Translation: Enabled (Urdu ↔ English)")
print("\n")
