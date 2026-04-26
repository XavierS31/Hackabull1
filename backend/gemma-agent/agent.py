import os
from google import genai
from google.genai import types
from hardware_tools import get_hardware_diagnostics, scan_qr_from_webcam
from dotenv import load_dotenv

load_dotenv()

class HardwareAgent:
    def __init__(self):
        self.client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
        self.model_id = "gemma-4-26b-a4b-it"
        
        # Define the tools available to Gemma
        self.tools = [types.Tool(
            function_declarations=[
                {
                    "name": "get_hardware_diagnostics",
                    "description": "Get status of hardware by device ID.",
                    "parameters": {
                        "type": "object",
                        "properties": {"device_id": {"type": "string"}},
                        "required": ["device_id"]
                    }
                },
                {
                    "name": "scan_qr_from_webcam",
                    "description": "Uses the camera to scan a physical QR code on equipment."
                }
            ]
        )]

    def run(self, prompt: str, image_path: str = None):
        contents = [prompt]
        
        # Attach image if provided
        if image_path:
            with open(image_path, "rb") as f:
                image_bytes = f.read()
            contents.append(types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg"))

        # High thinking for complex logic
        response = self.client.models.generate_content(
            model=self.model_id,
            contents=contents,
            config=types.GenerateContentConfig(
                tools=self.tools,
                thinking_config=types.ThinkingConfig(thinking_level="high"),
                system_instruction="You are a hardware expert. Use tools to diagnose issues."
            )
        )
        
        # Handle function calling
        if response.function_calls:
            for fc in response.function_calls:
                if fc.name == "get_hardware_diagnostics":
                    result = get_hardware_diagnostics(**fc.args)
                elif fc.name == "scan_qr_from_webcam":
                    result = scan_qr_from_webcam()
                
                # Feed the hardware result back to Gemma for a final answer
                return self.client.models.generate_content(
                    model=self.model_id,
                    contents=[prompt, types.Part.from_function_response(name=fc.name, response={"result": result})]
                ).text

        return response.text