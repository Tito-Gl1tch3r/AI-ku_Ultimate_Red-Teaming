from pydantic import BaseModel
import os

class Settings(BaseModel):
    db_host: str = os.getenv("DB_HOST", "db")
    db_port: int = int(os.getenv("DB_PORT", "5432"))
    db_name: str = os.getenv("DB_NAME", "tangled")
    db_user: str = os.getenv("DB_USER", "tangled")
    db_password: str = os.getenv("DB_PASSWORD", "P4ssw0rd!")

    jwt_secret: str = os.getenv("JWT_SECRET", "jwt_secret_change_me")
    jwt_expiration_seconds: int = 86400
    max_api_keys: int = int(os.getenv("MAX_API_KEYS", "10"))
    
    fernet_key: str = os.getenv("FERNET_KEY", "")
    api_cors_origins: str = os.getenv("API_CORS_ORIGINS", "http://localhost:8080")
    smtp_default_ehlo: str = os.getenv("SMTP_DEFAULT_EHLO_DOMAIN", "localhost")

    admin_email: str = os.getenv("ADMIN_EMAIL", "")
    admin_password: str = os.getenv("ADMIN_PASSWORD", "")

    default_mail_delay: float = float(os.getenv("DEFAULT_MAIL_DELAY", "0.3"))
    max_concurrent_campaigns: int = int(os.getenv("MAX_CONCURRENT_CAMPAIGNS", "10"))
    worker_shutdown_timeout: int = int(os.getenv("WORKER_SHUTDOWN_TIMEOUT", "10"))
    worker_poll_interval: float = float(os.getenv("WORKER_POLL_INTERVAL", "2.5"))

    scheduler_timezone: str = os.getenv("SCHEDULER_TIMEZONE", "UTC")

    default_prodid: str = "Microsoft Exchange Server 2019"

    @property
    def database_url(self) -> str:
        db_url = os.getenv("DATABASE_URL")
        if db_url:
            return db_url
        return f"postgresql+psycopg2://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"

settings = Settings()
