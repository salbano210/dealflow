"""Airtable sync layer.

SQLite is the source of truth. Airtable is a projected view.
Push (DB → Airtable) runs when you invoke a command.
Pull (Airtable → DB) reads human edits back.
"""
