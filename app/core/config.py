from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import computed_field

class Settings(BaseSettings):

    app_name: str = "jpico_url"
    model_config = SettingsConfigDict(env_file=".env")

    SECRET_KEY:str

    POSTGRES_SERVER: str
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str = ""
    POSTGRES_DB: str = ""

    REDIS_HOST: str
    REDIS_PORT: int
    CACHED_TTL_SECONDS : int

    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    JWT_REFRESH_TOKEN_EXPIRE_MINUTES: int = 10080
    JWT_ALGORITHM: str = "HS256"

    # # Worker
    # BATCH_SIZE: int|None=None
    # POLL_INTERVAL_MS: int|None=None


    @computed_field  # type: ignore[prop-decorator]
    @property
    def SQLALCHEMY_DATABASE_URI(self) -> str:
        return (
            f"postgresql+psycopg://{self.POSTGRES_USER}:"
            f"{self.POSTGRES_PASSWORD}@"
            f"{self.POSTGRES_SERVER}:"
            f"{self.POSTGRES_PORT}/"
            f"{self.POSTGRES_DB}"
        )
    
    # @computed_field  # type: ignore[prop-decorator]
    # @property
    # def REDIS_URI(self) -> str:
    #     return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}"

settings = Settings()
