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
            {"error": "Parametro 'state' mancante"},
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
                    "State non valido, scaduto "
                    "o già utilizzato"
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
            {"error": "Parametro 'code' mancante"},
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
        "Sessione Enable Banking salvata correttamente."
    )