# IOTA6910K Assignment 1

## Topic

This assignment focuses on distributed learning system design under a virtual geo-distributed GPU environment.

You are **not** asked to train a real large model. Instead, you will design a distributed training strategy, express the strategy clearly, and evaluate it with a Ray-based lightweight simulator that runs on a laptop.

## Problem Setting

You are given:

- a virtual geo-distributed GPU cluster made of multiple regions
- heterogeneous GPU types with different compute throughput and hourly cost
- different intra-region and inter-region bandwidth / latency
- a large-model training task described by model size, gradient size, and target training steps

Your task is to decide how to use the available resources efficiently.

## What You Should Do

You must complete four pieces of work.

### 1. Design a distributed training strategy

Your strategy should specify, at minimum:

- which clusters to use
- how many GPUs to use in each cluster
- how work is assigned across heterogeneous GPUs
- whether synchronization is flat or hierarchical
- how often global synchronization happens

### 2. Provide pseudocode

You must write system-level or algorithmic pseudocode for your strategy.

The pseudocode should make clear:

- how workers compute local updates
- how gradients or parameters are synchronized
- how cross-region communication is handled
- where your design differs from the provided baselines

### 3. Implement your strategy in the Ray simulator

You are given a Ray actor-based simulator starter. You must implement a custom strategy in:

- `strategies/student_custom_strategy.py`

Then run it against the required scenarios and compare it with the provided baselines. The Ray runtime is only used to simulate distributed execution roles such as workers, regional aggregators, and a global coordinator. You are not required to deploy a real cluster.

### 4. Analyze the results

You must compare your strategy with the baselines using the simulator outputs and explain:

- training time
- communication time
- communication volume
- GPU-hour cost
- tradeoffs between faster synchronization and convergence penalty

## Required Scenarios

You must run your strategy on both scenarios:

- `scenarios/world_mix.json`
- `scenarios/budget_pressure.json`

An additional optional stress-test scenario may be used for stronger analysis:

- `scenarios/regional_chokepoint.json`

## Provided Baselines

The starter includes three baselines:

1. `single_region_fastest`
2. `all_regions_flat_dp`
3. `all_regions_hierarchical_dp`

Your custom strategy must be compared against all three baselines.

## Files To Submit

Submit the following files and folders exactly:

1. `strategies/student_custom_strategy.py`
2. `report.pdf`
3. `outputs/world_mix_comparison.csv`
4. `outputs/budget_pressure_comparison.csv`

If you also analyze the optional scenario, you may additionally submit:

- `outputs/regional_chokepoint_comparison.csv`

Your `report.pdf` must contain:

1. a short description of the virtual cluster and training task
2. a clear description of your distributed training strategy
3. pseudocode for your strategy
4. tables or plots comparing your strategy with all baselines
5. a discussion of why your strategy performs better or worse
6. at least one failure case or limitation of your design

## How To Run

Run from the `Assignment 1/` folder.

Before you run the simulator, make sure you have:

- Python 3.10 or newer
- `pip`
- the package listed in `requirements.txt` (currently `ray`)

Recommended setup:

```bash
python3 -m venv .venv
. .venv/bin/activate
```

Then install the required dependency:

```bash
python3 -m pip install -r requirements.txt
```

No GPU is required. The Ray runtime is used only for local simulation on your laptop.

Baseline runs:

```bash
python3 scripts/run_baselines.py scenarios/world_mix.json
python3 scripts/run_baselines.py scenarios/budget_pressure.json
```

Custom strategy runs:

```bash
python3 scripts/run_custom.py scenarios/world_mix.json
python3 scripts/run_custom.py scenarios/budget_pressure.json
```

These commands write CSV summaries into `outputs/`.

They also write JSON trace files into `outputs/` so you can inspect the simulated worker / region / global synchronization events. Those trace files are optional and do not need to be submitted.

## What Counts As A Good Strategy

A strong strategy usually balances several factors rather than optimizing only one:

- use faster GPUs where they matter most
- avoid unnecessary cross-region synchronization
- reduce communication bottlenecks
- keep convergence penalty under control
- avoid exploding cost for small time gains

There is no single correct answer. The goal is to make a defensible system design and support it with simulation results.

## Grading Criteria

Total score: 100

| Component | What is evaluated | Points |
| --- | --- | ---: |
| Strategy design | Quality of the proposed distributed training plan; cluster selection, synchronization structure, and resource usage are coherent and well motivated | 25 |
| Pseudocode | Pseudocode is technically correct, clear, and reflects the actual proposed system behavior | 20 |
| Solution reasoning and analysis | Quality of tradeoff reasoning, explanation of results, and discussion of limitations or failure cases | 15 |
| Code implementation | `student_custom_strategy.py` runs correctly with the provided Ray simulator and produces valid comparison outputs | 20 |
| Experimental results | Required comparison CSV files are complete, baseline comparisons are correct, and reported metrics are used properly | 20 |

Interpretation:

- strategy design + pseudocode + reasoning = 60 points
- code + experimental results = 40 points

Strong submissions usually do two things well:

1. propose a sensible strategy for geo-distributed execution
2. explain clearly why the observed time / communication / cost tradeoffs make sense
