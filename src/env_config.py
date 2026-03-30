from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class PostgresConfig(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")
    host: str = Field(default="localhost", alias="POSTGRES_HOST")
    port: int = Field(default=5432, alias="POSTGRES_PORT")
    user: str = Field(default="postgres", alias="POSTGRES_USER")
    password: str = Field(alias="POSTGRES_PASSWORD")
    db: str = Field(alias="POSTGRES_DB")

    @property
    def url(self) -> str:
        return f"postgresql+asyncpg://{self.user}:{self.password}@{self.host}:{self.port}/{self.db}"


class RabbitConfig(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")
    host: str = Field(default="localhost", alias="RABBITMQ_HOST")
    port: int = Field(default=5672, alias="RABBITMQ_PORT")
    user: str = Field(default="guest", alias="RABBITMQ_USER")
    password: str = Field(default="guest", alias="RABBITMQ_PASSWORD")

    @property
    def url(self) -> str:
        return f"amqp://{self.user}:{self.password}@{self.host}:{self.port}/"


class RatingSystemConfig(BaseSettings):
    """Configuration for the rating system hyperparameters."""
    model_config = SettingsConfigDict(extra="ignore")

    r_min: float = Field(default=0.0, alias="RATING_R_MIN")
    r_max: float = Field(default=5000.0, alias="RATING_R_MAX")
    r_avg: float = Field(default=2400.0, alias="RATING_R_AVG")
    g: float = Field(default=0.5, alias="RATING_G")
    sigma_init: float = Field(default=25.0, alias="RATING_SIGMA_INIT")
    d: float = Field(default=4.0, alias="RATING_D")


class Env(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")
    rabbit: RabbitConfig = Field(default_factory=RabbitConfig)
    postgres: PostgresConfig = Field(default_factory=PostgresConfig)
    rating: RatingSystemConfig = Field(default_factory=RatingSystemConfig)


env = Env()
