# Reference Solution Idea

The reference solution does not simply use every cluster. It is intended to run on top of the student-side Ray simulator, where workers, regional aggregators, and the global coordinator are represented as Ray actors but the training metrics are still estimated analytically.

Core design principles:

- prefer proportional load balancing across heterogeneous GPU types
- avoid including distant clusters when their communication cost dominates their compute gain
- use hierarchical synchronization for multi-region execution
- increase synchronization interval moderately, but not so much that convergence penalty dominates

For `world_mix`, the reference strategy excludes the AP-SG cluster because its inter-region latency is too large relative to its compute contribution.

For `budget_pressure`, the reference strategy uses all premium GPUs and only part of the cheaper EU cluster, balancing cost and communication overhead.

These are not the only acceptable answers. Students can earn full credit with a different strategy if it is well reasoned and supported by results.
