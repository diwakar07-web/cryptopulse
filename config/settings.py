"""Central configuration loaded from environment variables."""
import os
from typing import List
from dotenv import load_dotenv

load_dotenv()


def _require(key: str) -> str:
    val = os.getenv(key)
    if not val:
        raise EnvironmentError(f"Required environment variable '{key}' is not set.")
    return val


class DBConfig:
    host: str = os.getenv("POSTGRES_HOST", "localhost")
    port: int = int(os.getenv("POSTGRES_PORT", "5432"))
    db: str = os.getenv("POSTGRES_DB", "cryptopulse")
    user: str = os.getenv("POSTGRES_USER", "cryptopulse")
    password: str = os.getenv("POSTGRES_PASSWORD", "cryptopulse_secret")

    @classmethod
    def url(cls) -> str:
        return (
            f"postgresql+psycopg2://{cls.user}:{cls.password}"
            f"@{cls.host}:{cls.port}/{cls.db}"
        )


class APIConfig:
    coingecko_base: str = os.getenv("COINGECKO_BASE_URL", "https://api.coingecko.com/api/v3")
    binance_base: str = os.getenv("BINANCE_BASE_URL", "https://api.binance.com/api/v3")
    fear_greed_base: str = os.getenv("FEAR_GREED_BASE_URL", "https://api.alternative.me")
    timeout: int = int(os.getenv("API_TIMEOUT", "30"))
    max_retries: int = int(os.getenv("API_MAX_RETRIES", "3"))


class ETLConfig:
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    price_spike_threshold: float = float(os.getenv("PRICE_SPIKE_THRESHOLD", "0.5"))
    volume_spike_threshold: float = float(os.getenv("VOLUME_SPIKE_THRESHOLD", "5.0"))
    # Coins to track
    coins: List[str] = [
        "bitcoin", "ethereum", "binancecoin", "ripple", "solana",
        "cardano", "polkadot", "dogecoin", "avalanche-2", "chainlink",
    ]
    # Binance trading pairs
    binance_symbols: List[str] = [
        "BTCUSDT", "ETHUSDT", "BNBUSDT", "XRPUSDT", "SOLUSDT",
        "ADAUSDT", "DOTUSDT", "DOGEUSDT", "AVAXUSDT", "LINKUSDT",
    ]
