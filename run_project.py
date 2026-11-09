%%writefile reproduce_all.py
import subprocess

def reproduce():
    print("Step 1: Generating data...")
    subprocess.run(["python", "generate_data.py"], check=True)

    print("Step 2: Running Part A (Data Cleaning & DB Storage)...")
    from part_a import run_part_a
    run_part_a()

    print("Step 3: Running Part B (Customer Segments & Lapse Prediction)...")
    from part_b import run_part_b
    run_part_b()

    print("Step 4: Running Part C (Support Ticket Triage)...")
    from part_c import run_part_c
    run_part_c()

    print("Step 5: Running Part D (Policy RAG & Refund Agent)...")
    from part_d import run_part_d
    run_part_d()

    print("ALL PIPELINE STEPS COMPLETED SUCCESSFULLY!")

if __name__ == "__main__":
    reproduce()

import subprocess

def reproduce():
    print("Step 1: Generating data...")
    subprocess.run(["python", "generate_data.py"], check=True)

    print("Step 2: Running Part A (Data Cleaning & DB Storage)...")
    from part_a import run_part_a
    run_part_a()

    print("Step 3: Running Part B (Customer Segments & Lapse Prediction)...")
    import importlib
    import part_b
    importlib.reload(part_b)
    part_b.run_part_b()

    print("Step 4: Running Part C (Support Ticket Triage)...")
    from part_c import run_part_c
    run_part_c()

    print("Step 5: Running Part D (Policy RAG & Refund Agent)...")
    from pard_d import run_part_d
    run_part_d()

    print("ALL PIPELINE STEPS COMPLETED SUCCESSFULLY!")

if __name__ == "__main__":
    reproduce()
