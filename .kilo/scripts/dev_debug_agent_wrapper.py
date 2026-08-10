import time
import subprocess
import sys
import os

if __name__ == "__main__":
    log_path = os.path.join(os.path.dirname(__file__), "..", "logs", "dev_debug_agent_wrapper.log")
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(f"WRAPPER STARTED at {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.flush()
        time.sleep(0.5)
        f.write(f"WRAPPER launching server at {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.flush()
        result = subprocess.run(
            [sys.executable, "D:/BikeMaster/dev_debug_agent.py"],
            cwd="D:/BikeMaster",
        )
        f.write(f"WRAPPER server exited with code {result.returncode} at {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        sys.exit(result.returncode)
