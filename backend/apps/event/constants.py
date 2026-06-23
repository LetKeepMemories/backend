"""EventType.slug -> public URL prefix.

Kept as a code-level mapping (rather than a DB field) so the EventType model
matches the spec exactly. Adding a new occasion type later (wedding,
graduation, ...) means adding one line here plus an EventType row — no
migration needed for the URL routing itself.
"""

EVENT_TYPE_URL_PREFIXES = {
    "birthday": "wishes",
    "memorial": "memorial",
    "anniversary": "anniversary",
}
