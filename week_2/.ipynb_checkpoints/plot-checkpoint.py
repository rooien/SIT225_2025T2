import pandas as pd
import matplotlib.pyplot as plt

df = pd.read_csv("accel_data.csv", header=None, names=["timestamp", "x", "y", "z"])
df["timestamp"] = pd.to_datetime(df["timestamp"])

plt.figure(figsize=(12, 6))
plt.plot(df["timestamp"], df["x"], label="X")
plt.plot(df["timestamp"], df["y"], label="Y")
plt.plot(df["timestamp"], df["z"], label="Z")
plt.xlabel("Time")
plt.ylabel("Acceleration (g)")
plt.title("Accelerometer Data (X, Y, Z)")
plt.legend()
plt.xticks(rotation=45)
plt.tight_layout()
plt.savefig("graphs.png")  # Optional: save graph to file
plt.show()
