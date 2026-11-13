"""Lead 4 (docs/PREREGISTRATION_v10.md): a counterfactual multi-agent reader.

Agents: the direct reader and the question-blind reader (both the frozen recipe adapter), a lesion segmenter
(the specialist), a counterfactual verifier (erase the claimed region, make an equal edit elsewhere, ask again),
and a trained deciding agent (the arbiter) that reads their reports.
"""
