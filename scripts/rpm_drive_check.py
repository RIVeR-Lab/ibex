import sys
import numpy as np, pandas as pd
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt

d = f'/home/river/ibex_analysis/{sys.argv[1]}/'
k = pd.read_csv(d + 'kairos_values.csv')
o = pd.read_csv(d + 'kiss_odometry.csv')

# Speed from odometry position (KISS-ICP may leave the twist fields empty)
o['speed'] = (np.hypot(o['pose.pose.position.x'].diff(), o['pose.pose.position.y'].diff())
              / o['t'].diff()).rolling(5, center=True).median()
m = pd.merge_asof(k[['t', 'rpm', 'throttle']].sort_values('t'),
                  o[['t', 'speed']].sort_values('t'), on='t')

moving = m.speed > 0.3   # m/s
print('rpm while stopped:\n', m.rpm[~moving].describe())
print('rpm while moving:\n', m.rpm[moving].describe())
print('correlation rpm vs speed: %.2f' % m.rpm.corr(m.speed))

fig, ax = plt.subplots(3, 1, sharex=True, figsize=(12, 8))
ax[0].plot(m.t, m.rpm); ax[0].set_ylabel('rpm')
ax[1].plot(m.t, m.throttle); ax[1].set_ylabel('throttle (commanded)')
ax[2].plot(m.t, m.speed); ax[2].set_ylabel('speed (m/s)'); ax[2].set_xlabel('t (s)')
fig.savefig(d + 'rpm_vs_driving.png', dpi=120)