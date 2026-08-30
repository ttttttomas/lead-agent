from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]
ENV_FILE = BACKEND_DIR / ".env"


class Settings(BaseSettings):
    nvidia_api_key: str = ""
    nvidia_base_url: str = "https://integrate.api.nvidia.com/v1"
    kimi_model: str = "moonshotai/kimi-k3"
    database_url: str = "sqlite:///./lead_agent.db"

    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    notification_email: str = ""

    # Automatic lead agent
    agent_scheduler_enabled: bool = True
    agent_schedule_hour: int = 9
    agent_schedule_minute: int = 0
    agent_timezone: str = "America/Argentina/Buenos_Aires"
    agent_industries: str = (
        "agencias de viajes,hoteles,inmobiliarias,constructoras,arquitectos,"
        "restaurantes,cafeterias,gimnasios,clinicas,dentistas,veterinarias,"
        "peluquerias,centros de estetica,concesionarias,talleres mecanicos,"
        "estudios contables,abogados,agencias de marketing,colegios,"
        "tiendas de ropa,mueblerias,ferreterias"
    )
    agent_cities: str = "Buenos Aires,Córdoba"
    agent_country: str = "Argentina"
    agent_leads_per_search: int = 3
    agent_minimum_score: int = 50
    agent_high_priority_score: int = 70
    agent_max_concurrency: int = 4

    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
