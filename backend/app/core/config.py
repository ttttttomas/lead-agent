from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    nvidia_api_key: str = ""
    nvidia_base_url: str = "https://integrate.api.nvidia.com/v1"
    kimi_model: str = "moonshotai/kimi-k3"
    database_url: str = "mysql+pymysql://user:password@localhost:3306/lead_agent"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
