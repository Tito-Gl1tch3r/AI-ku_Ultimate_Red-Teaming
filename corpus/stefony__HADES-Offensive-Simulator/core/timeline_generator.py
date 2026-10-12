import plotly.express as px
import pandas as pd
from datetime import datetime, timedelta

def generate_timeline(events):
    timeline_data = []

    for event in events:
        # Опит за извличане на timestamp от различни възможни места
        ts_raw = (
            event.get("timestamp") or
            event.get("sysmon", {}).get("time_generated")
        )

        # Ако няма timestamp, генерирай текущ
        if not ts_raw:
            ts_raw = datetime.now().isoformat()
            event["timestamp"] = ts_raw  # добави го обратно за бъдеща употреба

        try:
            ts_start = datetime.fromisoformat(ts_raw)
        except:
            continue  # пропускай невалидни формати

        ts_end = ts_start + timedelta(seconds=1)  # минимална продължителност

        timeline_data.append({
            "Start": ts_start,
            "End": ts_end,
            "Attack Type": event.get("attack", "Unknown"),
            "MITRE ID": event.get("mitre_id", event.get("technique", "")),
            "Detection": "✅ Detected" if event.get("sysmon", {}).get("detected", False) else "❌ Not Detected"
        })

    # Ако няма валидни данни, върни празен граф
    if not timeline_data:
        return px.scatter(title="⚠️ No valid events to visualize")

    df = pd.DataFrame(timeline_data)

    fig = px.timeline(
        df,
        x_start="Start",
        x_end="End",
        y="Attack Type",
        color="Detection",
        hover_data=["MITRE ID"]
    )
    fig.update_yaxes(autorange="reversed")
    fig.update_layout(title="📊 Attack Timeline Visualization")

    return fig
