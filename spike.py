import os
import sys
import time
from PIL import Image
import mss

try:
    import google.generativeai as genai
except ImportError:
    print("Error: google-generativeai is not installed. Run: pip install google-generativeai")
    sys.exit(1)

def main():
    # 1. API Key Setup
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("\033[93m⚠️  GEMINI_API_KEY environment variable is not set.\033[0m")
        api_key = input("Please enter your Gemini API Key: ").strip()
        if not api_key:
            print("\033[91m❌ API Key is required to run this script.\033[0m")
            print("Set it using: export GEMINI_API_KEY='your_api_key'")
            sys.exit(1)
    
    genai.configure(api_key=api_key)
    
    # 2. Get User Intent
    print("=" * 60)
    print("\033[94m🛡️  IntentGuard - Spike Prototype\033[0m")
    print("=" * 60)
    intent = input("What is your current work intent? (e.g., 'coding python', 'writing docs'): ").strip()
    if not intent:
        print("❌ Stated intent cannot be empty.")
        sys.exit(1)
        
    print(f"\n\033[92m✅ Intent registered: '{intent}'\033[0m")
    print("IntentGuard is now running. Press Ctrl+C to stop.")
    print("=" * 60)
    
    # Initialize the Gemini model dynamically by querying available models
    model_name = "gemini-3.5-flash"  # default fallback
    try:
        available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        flash_models = [m for m in available_models if "flash" in m]
        if flash_models:
            for pref in ["models/gemini-3.5-flash", "models/gemini-2.5-flash"]:
                if pref in flash_models:
                    model_name = pref
                    break
            else:
                model_name = flash_models[0]
    except Exception:
        # If API key does not support list_models, default to stable gemini-3.5-flash
        model_name = "gemini-3.5-flash"

    model = genai.GenerativeModel(
        model_name=model_name,
        system_instruction=(
            "You are IntentGuard, a productivity assistant. "
            "Your job is to look at a user's screen capture and determine if their current activity "
            "is aligned with their stated intent. Be reasonable but firm. For example, if they are "
            "in a code editor, terminal, or documentation page while they claim to be 'coding', "
            "they are ON TASK. If they are scrolling social media (Twitter/X, Reddit, etc.) or watching "
            "non-work videos, they are OFF TASK."
        )
    )
    
    loop_count = 0
    try:
        while True:
            loop_count += 1
            print(f"\n[{time.strftime('%H:%M:%S')}] Check #{loop_count}: Capturing screen...")
            
            # Take screenshot using mss
            with mss.MSS() as sct:
                # Grab primary monitor (monitor 1)
                monitor = sct.monitors[1]
                sct_img = sct.grab(monitor)
                
                # Convert raw pixels to PIL Image
                img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
                
                # Downscale for faster API upload and token savings
                img.thumbnail((1024, 1024))
            
            prompt = (
                f"The user's stated intent is: '{intent}'\n\n"
                "Analyze the provided screenshot and respond strictly in this format:\n"
                "STATUS: [ON_TASK / OFF_TASK]\n"
                "REASON: [Brief, 1-sentence explanation of what the user is doing and why they are on/off task]"
            )
            
            try:
                response = model.generate_content([prompt, img])
                result = response.text.strip()
                
                # Visual styling based on output status
                if "ON_TASK" in result:
                    print(f"\033[92m🟢 {result}\033[0m")
                elif "OFF_TASK" in result:
                    print(f"\033[91m🔴 {result}\033[0m")
                    # Play a simple terminal bell sound on macOS
                    print("\a", end="")
                    sys.stdout.flush()
                else:
                    print(result)
            except Exception as e:
                print(f"\033[91m❌ API request failed: {e}\033[0m")
            
            # Wait for 15 seconds before the next check
            time.sleep(15)
            
    except KeyboardInterrupt:
        print("\n\033[93m👋 IntentGuard stopped. Stay productive!\033[0m")

if __name__ == "__main__":
    main()
