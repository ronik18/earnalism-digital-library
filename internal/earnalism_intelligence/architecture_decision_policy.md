# Architecture Decision Policy

Prefer existing factory hooks, dashboards, and controlled publication manifests over parallel systems. Add small reusable policy helpers only when they improve release truth, cost control, or no-infinite-loop closure.

Generated release artifacts must remain out of git. Source changes should be testable, policy-driven, and reversible.
