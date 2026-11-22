"""
Executes cells of demo_orchestrator.ipynb and populates execution outputs directly into the notebook.
"""

import os
import sys
import json
import io
from contextlib import redirect_stdout, redirect_stderr

sys.path.insert(0, os.path.abspath("."))

def execute_notebook_in_place(nb_path: str):
    with open(nb_path, "r", encoding="utf-8") as f:
        nb = json.load(f)

    # Shared global namespace for execution
    exec_globals = {"__name__": "__main__", "__file__": nb_path}
    
    execution_count = 1
    for cell in nb.get("cells", []):
        if cell["cell_type"] == "code":
            source_code = "".join(cell["source"])
            stdout_capture = io.StringIO()
            stderr_capture = io.StringIO()
            
            try:
                with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
                    exec(source_code, exec_globals)
                out_str = stdout_capture.getvalue()
                err_str = stderr_capture.getvalue()
                
                outputs = []
                if out_str:
                    outputs.append({
                        "output_type": "stream",
                        "name": "stdout",
                        "text": [line + "\n" for line in out_str.splitlines()]
                    })
                if err_str:
                    outputs.append({
                        "output_type": "stream",
                        "name": "stderr",
                        "text": [line + "\n" for line in err_str.splitlines()]
                    })
                cell["outputs"] = outputs
                cell["execution_count"] = execution_count
                execution_count += 1
            except Exception as e:
                err_msg = f"{type(e).__name__}: {str(e)}"
                cell["outputs"] = [{
                    "output_type": "error",
                    "ename": type(e).__name__,
                    "evalue": str(e),
                    "traceback": [err_msg]
                }]
                print(f"[ERROR in cell {execution_count}]: {err_msg}")
                break

    with open(nb_path, "w", encoding="utf-8") as f:
        json.dump(nb, f, indent=2)
    print(f"[SUCCESS] Executed and populated outputs in {nb_path} ({execution_count - 1} code cells).")

if __name__ == "__main__":
    execute_notebook_in_place("notebooks/demo_orchestrator.ipynb")
    execute_notebook_in_place("demo_orchestrator.ipynb")
