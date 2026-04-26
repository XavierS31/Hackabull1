import os
from agent import HardwareAgent
from voice_engine import VoiceEngine

def main():
    # 1. Initialize the Brain
    print("--- Initializing Gemma 4 Hardware Agent ---")
    bot = HardwareAgent()
    voice = VoiceEngine()
    
    print("\nReady. You can ask me to:")
    print("- 'Scan the QR code on the device'")
    print("- 'Check the status of HW-99'")
    print("- 'Look at this photo and tell me if it's broken' (path/to/image.jpg)")
    
    while True:
        user_input = input("\nUser > ").strip()
        
        if user_input.lower() in ['exit', 'quit', 'q']:
            break
        
        # 2. Check if the user provided an image path in their prompt
        image_path = None
        words = user_input.split()
        for word in words:
            if word.endswith(('.jpg', '.jpeg', '.png')):
                image_path = word
                # Remove the filename from the text prompt so it doesn't confuse the model
                user_input = user_input.replace(word, "").strip()
        
        try:
            # 3. Send the request to the agent
            print("Gemma is thinking...")
            response = bot.run(user_input, image_path=image_path)
            
            print(f"\nAgent > {response}")
            
            voice.say(response)
            
        except Exception as e:
            print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()