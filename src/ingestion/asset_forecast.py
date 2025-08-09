from client import get_forecast
import pendulum

f = get_forecast(
    asset_id="WND-DE-003",
    version=pendulum.datetime(2025, 8, 9, 8, 30, tz="Europe/Berlin"),
)

print(f"Forecast for asset WND-DE-003 at 2025-06-08T08:15:00+02:00: {f}")