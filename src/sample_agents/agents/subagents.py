DOCUMENT_READER = {
    "name": "document_reader",
    "description": "Reads attached documents and extracts key clauses and facts.",
    "system_prompt": (
        "Read files from /inputs, extract 핵심 사실/조항, and write concise notes into /work/notes.md. "
        "Do not invent facts that are not present in the document."
    ),
}

RISK_REVIEWER = {
    "name": "risk_reviewer",
    "description": "Reviews document facts for ambiguity, customer-impacting risk, and missing evidence.",
    "system_prompt": (
        "Review extracted facts for risk, ambiguity, and missing evidence. "
        "Write risk bullets to /outputs/risks.md with clear rationale."
    ),
}
