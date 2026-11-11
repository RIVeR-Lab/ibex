import pandas as pd
d = pd.read_csv('~/ibex_analysis/steering_wheel_sweep_01/steering_aligned.csv')
print((d.steerang - d.out_joy_steer).abs().describe())