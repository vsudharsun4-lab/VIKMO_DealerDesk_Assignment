"""Conversation memory model for the Dealer Assistant."""
from django.db import models


class ChatSession(models.Model):
    """Stores serialised conversation history per session_id."""
    session_id = models.CharField(max_length=255, unique=True, db_index=True)
    history_json = models.TextField(default="[]")  # JSON list of {role, parts}
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "assistant_chat_session"

    def __str__(self):
        return self.session_id
