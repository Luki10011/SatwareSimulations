import pandas as pd
import matplotlib.pyplot as plt

csv_file = "data\\SimulationData\\rw\\rw_speed.csv"

df = pd.read_csv(csv_file)

x = df.iloc[:, 0]

plt.figure(figsize=(10, 6))
offset = 5000

for i, column in enumerate(df.columns[1:]):
    if i % 2 == 0:
        plt.plot(x[-offset:], df[column][-offset:], label=column[:-2])

# Opisy osi
plt.xlabel("Time [s]")
plt.ylabel("RW Angular Velocity [deg/s]")

plt.legend()

plt.grid(True)

plt.tight_layout()

plt.show()