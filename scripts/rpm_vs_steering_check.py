import pandas as pd
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt

d = '/home/river/ibex_analysis/steering_wheel_sweep_01/'
k = pd.read_csv(d + 'kairos_values.csv')
a = pd.read_csv(d + 'steering_aligned.csv')
m = pd.merge_asof(k[['t', 'rpm', 'key_on', 'eng_enb']].sort_values('t'),
                  a[['t', 'out_joy_steer']].sort_values('t'), on='t')

print('all multiples of 8:', (m.rpm % 8 == 0).all())
moving = m.out_joy_steer.diff().abs() > 1          # steering command changing
print('mean rpm  steering moving: %.1f   steering still: %.1f'
      % (m.rpm[moving].mean(), m.rpm[~moving].mean()))
print(m[['key_on', 'eng_enb']].drop_duplicates())

fig, ax = plt.subplots(2, 1, sharex=True, figsize=(12, 6))
ax[0].plot(m.t, m.rpm); ax[0].set_ylabel('rpm')
ax[1].plot(m.t, m.out_joy_steer); ax[1].set_ylabel('steer command')
ax[1].set_xlabel('t (s)')
fig.savefig('rpm_vs_steering.png', dpi=120)