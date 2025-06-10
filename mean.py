import numpy as np

cp_sr = [0.526, 0.554, 0.502, 0.534, 0.575, 0.562, 0.484, 0.643, 0.464, 0.490, 0.517, 0.409]
ilp_sr = [0.526, 0.554, 0.502, 0.529, 0.560, 0.512, 0.423, 0.568, 0.379, 0.373, 0.366, 0.425]

cp_above = [94.4, 90.5, 85.7, 80.7, 86.4, 82.8, 65.3, 78.9, 73.8, 84.3, 86.9, 42.6]
ilp_above = [94.4, 90.5, 85.7, 82.4, 89.8, 79.7, 50.7,  97.4, 47.5, 45.8, 34.5, 44.7]

# Satisfaction Rate
cp_sr_mean = np.mean(cp_sr)
cp_sr_std = np.std(cp_sr)
ilp_sr_mean = np.mean(ilp_sr)
ilp_sr_std = np.mean(ilp_sr)

# Above mninimum
cp_above_mean = np.mean(cp_above)
cp_above_std = np.std(cp_above)
ilp_above_mean = np.mean(ilp_above)
ilp_above_std = np.std(ilp_above)



print("CP")
print(f"mean satisfaction rate: {cp_sr_mean}")
print(f"std satisfaction rate: {cp_sr_std}")
print(f"mean above minimum percentage: {cp_above_mean}")
print(f"std above minimum percentage: {cp_above_std}")


print("ILP")
print(f"mean satisfaction rate: {ilp_sr_mean}")
print(f"std satisfaction rate: {ilp_sr_std}")
print(f"mean above minimum percentage: {ilp_above_mean}")
print(f"std above minimum percentage: {ilp_above_std}")






