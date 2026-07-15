"""Fear & Greed Index API extractor."""
import logging
from datetime import datetime, timezone

import pandas as pd

from config.settings import APIConfig
from etl.extract.http_client import get_json

logger = logging.getLogger(__name__)

BASE = APIConfig.fear_greed_base
SOURCE = "alternative_me"


def fetch_fear_greed(limit: int = 30) -> pd.DataFrame:
    """Fetch last `limit` days of Fear & Greed index values."""
    url = f"{BASE}/fng/"
    data = get_json(url, params={"limit": limit, "format": "json"})
    rows = []
    for item in data.get("data", []):
        ts = datetime.fromtimestamp(int(item["timestamp"]), tz=timezone.utc)
        rows.append(
            {
                "index_value": int(item["value"]),
                "classification": item.get("value_classification", ""),
                "timestamp": ts,
                "source": SOURCE,
            }
        )
    df = pd.DataFrame(rows)
    logger.info("Fear & Greed: %d rows extracted", len(df))
    return df
