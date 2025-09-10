import datetime

from picterra import TracerClient

# Replace this with the id of the plots group to analyze
plots_group_id = "3c3d947c-d982-4af7-ac09-00806b81a216"

client = TracerClient()

print("Starting analysis...")
url = client.analyze_plots(
    plots_group_id,
    "New analysis",
    ["plotid_1", "plotid_2", "plotid_3"],
    datetime.date.fromisoformat("2022-01-01"),
    datetime.date.fromisoformat("2024-01-01")
)["url"]


print("Analysis completed: you can open it at the following URL:" + url)
