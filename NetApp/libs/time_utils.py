import datetime

def to_epoch_ms(dt: datetime) -> int:
    return int(dt.timestamp() * 1000)