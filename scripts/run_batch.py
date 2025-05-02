import subprocess
from datetime import datetime
import os

# All schools in the processed_data folder
processed_data_path = "data/processed_data"
schools = [
    name for name in os.listdir(processed_data_path)
    if os.path.isdir(os.path.join(processed_data_path, name))]

# schools = ["school_5"]

methods = ["cp", "milp", "random"]
repeats = 10
time_limit = 30 * 60


timestamp = datetime.now().strftime("%m-%d_%H:%M")
log_file = f"scripts/batch_log_{timestamp}.txt"

with open(log_file, "w") as log:
    for school in schools:
        for method in methods:
            for i in range(repeats):
                log.write(f"\n=== Running: {school}, {method}, run {i+1} ===\n")
                print(f"Running: {school}, {method}, run {i+1}")

                # Call the main.py script
                result = subprocess.run(
                    ["python3", "main.py", school, method, str(time_limit)],
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

                log.write(result.stdout)
                log.write("\n" + "="*50 + "\n")

print(f"Batch run complete. Logs saved to: {log_file}")
