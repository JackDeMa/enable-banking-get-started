from django.http import (
    HttpResponse,
    HttpResponseRedirect,
    JsonResponse,
)

from enable_banking.client import EnableBankingClient
from enable_banking.config import Settings
from enable_banking.storage import (
    consume_authorization_flow,
    save_session,
)

def enable_banking_callback(request):
    settings = Settings.from_env()
    state = request.GET.get("state")
    if not state:
        return JsonResponse(
            {"error": "Missing 'state' parameter"},
            status=400,
        )

    bank_key = consume_authorization_flow(
        state,
        settings.session_database,
    )
    if bank_key is None:
        return JsonResponse(
            {
                "error": (
                    "Invalid, expired "
                    "or already used state"
                )
            },
            status=400,
        )

    error = request.GET.get("error")

    if error:
        return JsonResponse(
            {
                "error": error,
                "description": request.GET.get(
                    "error_description"
                    ),
            },
            status=400,
        )

    code = request.GET.get("code")

    if not code:
        return JsonResponse(
            {"error": "Missing 'code' parameter"},
            status=400,
        )

    client = EnableBankingClient(settings)
    session = client.authorize_session(code)

    save_session(
        session,
        settings.session_database,
    )
    return HttpResponseRedirect("/connection/success")

def connection_success(request):
    return HttpResponse(
        "Enable Banking session saved successfully."
    )