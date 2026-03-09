# IOTA6910K Assignment 1

## Topic

This assignment focuses on distributed learning system design under a virtual geo-distributed GPU environment.

You are **not** asked to train a real large model. Instead, you will design a distributed training strategy, express the strategy clearly, and evaluate it with a lightweight simulator.

## Problem Setting

You are given:

- a virtual geo-distributed GPU cluster made of multiple regions
- heterogeneous GPU types with different compute throughput and hourly cost
- different intra-region and inter-region bandwidth / latency
- a large-model training task described by model size, gradient size, and target training steps

Your task is to decide how to use the available resources efficiently.

## What You Must Do

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

### 3. Implement your strategy in the simulator

You are given a simulator starter. You must implement a custom strategy in:

- `strategies/student_custom_strategy.py`

Then run it against the required scenarios and compare it with the provided baselines.

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

## Provided Baselines

The starter includes three baselines:

1. `single_region_fastest`
2. `all_regions_flat_dp`
3. `all_regions_hierarchical_dp`

Your custom strategy must be compared against all three baselines.

## Deliverables

Submit the following:

1. Your completed code
2. A report in PDF
3. The generated CSV summary files for both scenarios

Your report must contain:

1. A short description of the virtual cluster and task
2. A clear description of your strategy
3. Pseudocode for your strategy
4. Tables or plots comparing your strategy with the baselines
5. A discussion of why your strategy performs better or worse
6. At least one failure case or limitation of your design

## How To Run

Run from the `student/` folder.

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

## What Counts As A Good Strategy

A strong strategy usually balances several factors rather than optimizing only one:

- use faster GPUs where they matter most
- avoid unnecessary cross-region synchronization
- reduce communication bottlenecks
- keep convergence penalty under control
- avoid exploding cost for small time gains

There is no single correct answer. The goal is to make a defensible system design and support it with simulation results.

## Grading Criteria

Your submission will be graded on:

1. correctness and completeness of the simulator-based implementation
2. quality of the strategy design
3. quality and clarity of the pseudocode
4. correctness and depth of the experimental comparison
5. quality of the analysis and discussion

