# Evaluation harness

Empty in v0.1 by design — there's no retrieval or generation pipeline
yet to evaluate.

Planned structure (introduced starting v0.3, populated starting v0.4):

```text
evals/
├── datasets/     # questions.json: question, expected_answer,
│                 # relevant_document, relevant_chunk(s)
├── retrieval/    # retrieval runner + Recall@K, MRR, NDCG@K
├── generation/   # answer relevance, faithfulness, citation correctness
├── metrics/      # shared metric implementations
└── reports/      # versioned baseline comparisons (one variable changed
                   # at a time — see docs/architecture.md)
```

The evaluation harness consumes the same `RAG` interfaces the
production application uses — it does not fork its own copy of
retrieval/generation logic, and the production code contains no
`if evaluation_mode:` branches.

See `docs/architecture.md` for the full evaluation timeline and the
"one variable at a time" experimental discipline.
