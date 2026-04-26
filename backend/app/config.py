from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    gemini_api_key: str = ""
    google_api_key: str = ""
    gemma_model: str = "gemma-4"
    allowed_origins: str = "http://localhost:5173"
    events_dir: str = "data/events"
    fall_threshold_g: float = 2.4
    pre_event_seconds: int = 10
    post_event_seconds: int = 10
    imu_udp_host: str = "0.0.0.0"
    imu_udp_port: int = 9002
    glasses_stream_url: str = ""
    glove_stream_url: str = ""
    # Hardware node IPs (used to send commands back to ESP32 nodes)
    glove_ip: str = "192.168.4.11"
    glasses_ip: str = "192.168.4.10"
    # ElevenLabs voice
    elevenlabs_api_key: str = ""
    elevenlabs_voice_id: str = "JBFqnCBsd6RMkjVDRZzb"  # George
    elevenlabs_model: str = "eleven_flash_v2_5"
    # Firebase (optional — falls back to local storage when empty)
    firebase_service_account: str = ""  # path to service-account JSON
    firebase_storage_bucket: str = ""   # e.g. "your-project.appspot.com"

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]

    @property
    def effective_api_key(self) -> str:
        return self.gemini_api_key or self.google_api_key


# ---------- System prompts ----------

ONBOARDING_PROMPT = """
You are an onboarding classifier for a medical agentic assistant system for dementia patients.
Return JSON only. Do not include markdown. Schema:
{
  "patient_profile": {
    "name": "string",
    "dob": "string",
    "conditions": ["string"],
    "allergies": ["string"],
    "medications": ["string"],
    "emergency_contact": "string"
  },
  "active_agents": [
    {
      "name": "Chatbot | Falling Agent | Conversation Agent | Vision Agent | Tracking Dementia",
      "enabled": true,
      "reason": "string"
    }
  ],
  "thinking": [
    "Step-by-step reasoning sentence 1",
    "Step-by-step reasoning sentence 2"
  ]
}
Always include at least one active agent.
""".strip()

CHATBOT_SYSTEM = (
    "You are a compassionate AI assistant for a dementia patient wearing smart glasses and a glove with sensors. "
    "You help caregivers and family members understand what the patient is experiencing. "
    "Be concise, warm, and helpful. If you receive an image, describe the surroundings clearly."
)

VISION_SYSTEM = (
    "You are a vision assistant for a dementia patient. "
    "Describe the surroundings clearly and concisely to help the patient navigate safely. "
    "Mention any obstacles, people, or important objects. Keep it under 3 sentences."
)

CONVERSATION_SYSTEM = (
    "You are a conversation companion for a dementia patient. "
    "Look at what the patient sees and start a friendly, encouraging conversation about it. "
    "Be warm, simple, and help them engage with their surroundings."
)

TRACKING_SYSTEM = (
    "You are a dementia tracking assistant. You have access to the patient's recent activity log. "
    "Answer questions about what happened, when, and why based on the log provided. "
    "Be clear and compassionate."
)

settings = Settings()
