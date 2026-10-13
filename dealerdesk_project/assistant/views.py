"""Assistant views — §9."""
from rest_framework.response import Response
from rest_framework.views import APIView

from .agent import run_assistant


def err(code, message, details=None, http_status=400):
    return Response(
        {"error": {"code": code, "message": message, "details": details or []}},
        status=http_status,
    )


class AssistantChatView(APIView):
    """POST /api/assistant/chat/"""

    def post(self, request):
        session_id = request.data.get("session_id")
        dealer_id = request.data.get("dealer_id")
        message = request.data.get("message", "").strip()

        if not session_id:
            return err("VALIDATION_ERROR", "session_id is required.")
        if not dealer_id:
            return err("VALIDATION_ERROR", "dealer_id is required.")
        if not message:
            return err("VALIDATION_ERROR", "message is required.")

        from products.models import Dealer
        try:
            Dealer.objects.get(pk=dealer_id)
        except Dealer.DoesNotExist:
            return err("VALIDATION_ERROR", f"Dealer {dealer_id} not found.")

        result = run_assistant(
            session_id=str(session_id),
            dealer_id=int(dealer_id),
            message=message,
        )
        return Response(result)
