"""Pipeline steps.

Each step is a plain function operating on a company. Steps are the
deterministic glue; LLM calls happen only inside specific steps
(extract, score, research, outreach).
"""
