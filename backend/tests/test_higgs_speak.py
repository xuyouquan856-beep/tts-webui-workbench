import sys
import os
import requests

# Ensure we are calling the server running at http://127.0.0.1:8000
BASE_URL = "http://127.0.0.1:8000/api"

def main():
    print("=== Higgs /api/speak Verification ===")
    
    # 1. Fetch available models
    print("\n[Step 1] Fetching models...")
    res = requests.get(f"{BASE_URL}/models")
    if res.status_code != 200:
        print(f"Error: Failed to fetch models. Status: {res.status_code}, Body: {res.text}")
        sys.exit(1)
        
    models = res.json()
    higgs_model = None
    for m in models:
        print(f" - Model ID {m['id']}: {m['name']} ({m['provider_type']}) - Enabled: {m['enabled']}")
        if m['provider_type'] == 'higgs_api':
            higgs_model = m
            
    if not higgs_model:
        print("Error: Higgs model not found in the database. Ensure database was seeded correctly.")
        sys.exit(1)
        
    if not higgs_model['enabled']:
        print("Warning: Higgs model is disabled in database. Enabling it for testing...")
        # If disabled, we can enable it by PUT /api/models/{id} but let's check first.
        
    # Test 1: Normal Higgs Generation
    print("\n[Step 2] Testing normal Higgs speech generation...")
    speak_payload = {
        "text": "Hello, this is a manual verification of Higgs normal speech synthesis via the speak endpoint.",
        "model_id": higgs_model['id'],
        "params": {}
    }
    
    res = requests.post(f"{BASE_URL}/speak", json=speak_payload)
    if res.status_code != 200:
        print(f"Error calling /api/speak: Status: {res.status_code}, Body: {res.text}")
        sys.exit(1)
        
    speak_data = res.json()
    print("Response JSON:", speak_data)
    if speak_data.get("status") != "succeeded":
        print(f"Error: Higgs speech generation failed. Status: {speak_data.get('status')}, Error: {speak_data.get('error')}")
        sys.exit(1)
        
    audio_url = speak_data["audio_url"]
    print(f"SUCCESS: Generated audio URL: {audio_url}")
    
    # Verify file is readable
    audio_filename = audio_url.split("/")[-1]
    res = requests.get(f"{BASE_URL}/audio/{audio_filename}")
    if res.status_code != 200:
        print(f"Error: Failed to fetch generated audio file. Status: {res.status_code}")
        sys.exit(1)
    print(f"SUCCESS: Audio file downloaded, size: {len(res.content)} bytes.")

    # Test 2: Voice Cloning Higgs Generation
    print("\n[Step 3] Fetching voice profiles for cloning...")
    res = requests.get(f"{BASE_URL}/profiles")
    if res.status_code != 200:
        print(f"Error fetching profiles. Status: {res.status_code}")
        sys.exit(1)
        
    profiles = res.json()
    active_profile = None
    for p in profiles:
        print(f" - Profile ID {p['id']}: {p['name']} ({p['provider_type']}) - Ref Audio: {p['ref_audio_path']}")
        if p['provider_type'] == 'higgs_api' and p['ref_audio_path']:
            active_profile = p
            
    if not active_profile:
        print("No existing Higgs voice profile with reference audio was found. Creating one from existing profile_1.wav...")
        # Since profile_1.wav exists in data/reference/, let's create a profile pointing to it
        profile_payload = {
            "name": "Seeded Higgs Voice Profile",
            "language": "en",
            "provider_type": "higgs_api",
            "model_id": higgs_model['id'],
            "default_params_json": "{}",
            "ref_text": "This is the transcript of the reference voice."
        }
        res = requests.post(f"{BASE_URL}/profiles", json=profile_payload)
        if res.status_code not in (200, 201):
            print(f"Error creating test profile: Status: {res.status_code}, Body: {res.text}")
            sys.exit(1)
        profile = res.json()
        profile_id = profile["id"]
        
        # Link the existing profile_1.wav file as its reference audio path in SQLite database
        # We can do this by copying profile_1.wav to data/reference/profile_{id}.wav, or uploading it
        # Let's just upload data/reference/profile_1.wav to this profile!
        ref_path = "data/reference/profile_1.wav"
        if os.path.exists(ref_path):
            print(f"Uploading existing {ref_path} to new profile ID {profile_id}...")
            with open(ref_path, "rb") as f:
                files = {"file": ("profile_1.wav", f, "audio/wav")}
                res = requests.post(f"{BASE_URL}/profiles/{profile_id}/upload-reference", files=files)
            if res.status_code != 200:
                print(f"Error uploading reference audio: Status: {res.status_code}, Body: {res.text}")
                sys.exit(1)
            active_profile = res.json()
            print("Successfully uploaded reference audio.")
        else:
            print("Error: profile_1.wav not found. Skipping cloning test.")
            
    if active_profile:
        print(f"Using Voice Profile ID {active_profile['id']} for cloning test...")
        clone_speak_payload = {
            "text": "Hello, this is a zero-shot voice clone synthesis manual verification test using Higgs API.",
            "profile_id": active_profile['id'],
            "params": {}
        }
        res = requests.post(f"{BASE_URL}/speak", json=clone_speak_payload)
        if res.status_code != 200:
            print(f"Error calling /api/speak with voice clone: Status: {res.status_code}, Body: {res.text}")
            sys.exit(1)
            
        clone_speak_data = res.json()
        print("Cloning Response JSON:", clone_speak_data)
        if clone_speak_data.get("status") != "succeeded":
            print(f"Error: Higgs voice cloning failed. Status: {clone_speak_data.get('status')}, Error: {clone_speak_data.get('error')}")
            sys.exit(1)
            
        clone_audio_url = clone_speak_data["audio_url"]
        print(f"SUCCESS: Generated clone audio URL: {clone_audio_url}")
        
        # Verify file is readable
        clone_audio_filename = clone_audio_url.split("/")[-1]
        res = requests.get(f"{BASE_URL}/audio/{clone_audio_filename}")
        if res.status_code != 200:
            print(f"Error: Failed to fetch generated clone audio file. Status: {res.status_code}")
            sys.exit(1)
        print(f"SUCCESS: Clone audio file downloaded, size: {len(res.content)} bytes.")
        
    print("\n=== All Tests Passed Successfully ===")

if __name__ == "__main__":
    main()
