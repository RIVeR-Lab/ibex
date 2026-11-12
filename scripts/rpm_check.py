import pandas as pd
k = pd.read_csv('~/ibex_analysis/steering_wheel_sweep_01/kairos_values.csv')
print(k['rpm'].describe())
print(k['rpm'].value_counts().head(10))