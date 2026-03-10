# Learning Goals

This assignment is designed to evaluate whether students can reason about distributed training as a systems problem rather than as a pure model-training exercise.

The Ray requirement is meant to expose students to a realistic control-plane abstraction for distributed execution without requiring a real multi-node deployment.

Expected learning outcomes:

- understand why geo-distributed training is limited by communication, not just compute
- reason about heterogeneous GPU pools and resource selection
- explain the tradeoff between synchronization frequency and convergence behavior
- compare flat and hierarchical synchronization schemes
- articulate why the fastest strategy in wall-clock time is not always the best strategy under cost or convergence constraints

Expected insight:

Students should recognize that naive use of all available clusters is often a poor design because long-haul communication can dominate step time.
