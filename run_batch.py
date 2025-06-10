import subprocess
from datetime import datetime

# Setup
tasks = [
    ("WegwijzerBB2", "cp"),
    ("WegwijzerBB2", "ilp"),
    ("WegwijzerMB", "cp"),
    ("WegwijzerMB", "ilp"),
    ("synthetic_school_45", "cp"),
    ("synthetic_school_45", "ilp"),
    ("synthetic_school_57", "cp"),
    ("synthetic_school_57", "ilp"),
    ("synthetic_school_63", "cp"),
    ("synthetic_school_63", "ilp"),
    ("synthetic_school_69", "cp"),
    ("synthetic_school_69", "ilp"),
    ("synthetic_school_75", "cp"),
    ("synthetic_school_75", "ilp"),
    ("synthetic_school_82", "cp"),
    ("synthetic_school_82", "ilp"),
    ("synthetic_school_88", "cp"),
    ("synthetic_school_88", "ilp"),
    ("synthetic_school_94", "cp"),
    ("synthetic_school_94", "ilp"),
    ("synthetic_school_100", "cp"),
    ("synthetic_school_100", "ilp"),
]

# Run each task
for school, method in tasks:
    print(f"\n=== Running: {school}, {method} ===\n")

    subprocess.run(["python3", "main.py", school, method], check=True)

print(f"Batch run complete")
