"""One-off calibration: print retrieved distances for in-scope vs out-of-scope questions."""
from app.agent.retriever import search_policies

IN_SCOPE = [
    ("employee", "How many annual leave days am I entitled to per year?"),
    ("employee", "What is the code of conduct about gifts?"),
    ("employee", "What are the working hours for remote work?"),
    ("hr", "What is the annual performance bonus percentage?"),
    ("hr", "When must a personal data breach be reported?"),
    ("admin", "What are the RTO and RPO targets for critical services?"),
    ("admin", "How often is privileged access recertified?"),
    ("admin", "What are the patching SLAs for critical vulnerabilities?"),
    ("employee", "How long is parental leave?"),
    ("employee", "What is the notice period during probation?"),
]

OUT_OF_SCOPE = [
    ("employee", "What is the capital of France?"),
    ("employee", "How do I cook pasta?"),
    ("employee", "Who won the football world cup in 2022?"),
    ("employee", "What is the weather today?"),
    ("hr", "Tell me a joke about cats."),
    ("employee", "What is 2 + 2?"),
    ("admin", "What is the price of bitcoin?"),
    ("employee", "Can you recommend a good movie?"),
]

for role, q in IN_SCOPE:
    hits = search_policies(q, role, k=3)
    print(f"[IN ] {role:8s} min={min(h['distance'] for h in hits):.3f} | {q}")

print()
for role, q in OUT_OF_SCOPE:
    hits = search_policies(q, role, k=3)
    print(f"[OUT] {role:8s} min={min(h['distance'] for h in hits):.3f} | {q}")
