from django.http import JsonResponse

from enable_banking.client import EnableBankingClient
from enable_banking.config import Settings
from enable_banking.storage import save_session

def enable_banking_callback(request):
    error = request.GET.get("error")

    if error:
        return JsonResponse(
            {
                "error": error,
                "description": request.GET.get("error_description"),
            },
            status=400,
        )

    code = request.GET.get("code")

    if not code:
        return JsonResponse(
            {"error": "Parametro 'code' mancante"},
            status=400,
        )

    settings = Settings.from_env()
    client = EnableBankingClient(settings)

    session = client.authorize_session(code)

    save_session(
        session,
        settings.session_database,
    )
    return JsonResponse(session)
