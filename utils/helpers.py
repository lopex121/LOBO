def format_time(ts):
    from datetime import datetime
    return datetime.fromisoformat(ts).strftime('%Y-%m-%d %H:%M:%S')