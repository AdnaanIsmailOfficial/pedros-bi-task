import subprocess
import sys

# Runs the whole pipeline in order. If any step fails, including a failed data check,
# everything after it is skipped.
steps = ["01_land_raw.py", "02_stage.py", "03_model.py", "04_checks.py"]

for step in steps:
    print(f"\n######## {step} ########", flush=True)
    result = subprocess.run([sys.executable, step])
    if result.returncode != 0:
        raise SystemExit(f"\nPipeline stopped at {step}. Later steps did not run.")

print("\nPipeline finished. All steps ran and all checks passed.")
