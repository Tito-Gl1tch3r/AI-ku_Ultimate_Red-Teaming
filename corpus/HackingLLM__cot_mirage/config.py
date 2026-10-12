import os

from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class Config:
    """Simple configuration management"""

    # API Configuration
    CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

    # Processing Configuration
    LLM_RETRY_COUNT = int(os.getenv("LLM_RETRY_COUNT", "3"))
    API_RETRY_COUNT = int(os.getenv("API_RETRY_COUNT", "3"))
    API_INTERVAL = float(os.getenv("API_INTERVAL", "2.0"))
    MAX_JUDGER_RETRIES = int(os.getenv("MAX_JUDGER_RETRIES", "10"))

    # hardcoded for now
    CLAUDE_API_URL = "https://api.anthropic.com/v1/messages"
    MODEL_ID = "openai/gpt-oss-20b"

    # Validate required settings
    @classmethod
    def validate(cls):
        if not cls.CLAUDE_API_KEY:
            raise ValueError("CLAUDE_API_KEY environment variable is required")
        if not cls.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY environment variable is required")
        return True


config = Config()
