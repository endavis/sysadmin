import logging
from datetime import datetime, timedelta, timezone

from  libs.time_utils import to_epoch_ms

def post(
    client,
    category: str,
    measurement: str,
    metrics: list,
    filter_expr: str,
    interval: str = "60s",
    start_time: str = None,
    end_time: str = None,
    lookback_minutes: int = None
) -> dict:
    if start_time and end_time:
        # Expecting ISO 8601 format: "YYYY-MM-DDTHH:MM:SSZ"
        start = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
        end = datetime.fromisoformat(end_time.replace("Z", "+00:00"))
    elif lookback_minutes:
        end = datetime.now(timezone.utc)
        start = end - timedelta(minutes=lookback_minutes)
    else:
        raise ValueError("Either start_time and end_time or lookback_minutes must be provided.")

    start_ms = to_epoch_ms(start)
    end_ms = to_epoch_ms(end)
    max_points = int((end_ms - start_ms) / 60000)  # 1 point per minute

    results = {}
    for metric in metrics:
        payload = {
            "category": category,
            "measurement": measurement,
            "metric": metric,
            "filter": filter_expr,
            "fromTimeMs": start_ms,
            "toTimeMs": end_ms,
            "timeAggregationInterval": interval,
            "maxNumberOfDataPoints": max_points,
            "detectAnomalies": False,
            "interpolationType": "NONE"
        }

        try:
            response = client.call_endpoint(
                "/rest/v1/lake/query/timeseries",
                method="POST",
                body=payload
            )
            if not response:
                logging.debug(f"no data for {category}:{measurement}:{metric} with {filter_expr}")
            results[metric] = response
        except Exception as e:
            logging.error(f"Error querying metric {metric}: {e}")
            results[metric] = None

    return results