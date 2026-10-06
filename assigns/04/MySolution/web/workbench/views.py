"""Django HTTP boundary; the controller and model own source behavior."""
import json
from django.core.exceptions import RequestDataTooBig
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET, require_http_methods, require_POST
from .controller import SourceController
from .source import SourceConflict, SourceError, SourceModel

source_model = SourceModel()  # Local, single-user state; discarded on server restart.
MAX_REQUEST_BYTES = 2 * 1024 * 1024


def response(error=None, status=200):
    payload = {"state": source_model.snapshot()}
    if error:
        payload["error"] = error
    return JsonResponse(payload, status=status)


def data(request):
    if int(request.META.get("CONTENT_LENGTH") or 0) > MAX_REQUEST_BYTES:
        raise RequestDataTooBig()
    try:
        payload = json.loads(request.body)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise SourceError("Request must contain valid JSON.") from exc
    if not isinstance(payload, dict):
        raise SourceError("Request must contain a JSON object.")
    return payload


def version(value):
    if type(value) is not int or value < 0:
        raise SourceError("A valid source state version is required.")
    return value


@require_GET
@ensure_csrf_cookie
def index(request):
    return render(request, "index.html", {"source_state": source_model.snapshot()})


@require_http_methods(["GET", "POST"])
def source(request):
    if request.method == "GET":
        return response()
    controller = SourceController(source_model)
    try:
        if int(request.META.get("CONTENT_LENGTH") or 0) > MAX_REQUEST_BYTES:
            raise RequestDataTooBig()
        if request.content_type == "multipart/form-data":
            file = request.FILES.get("file")
            if file is None:
                raise SourceError("Choose a UTF-8 source file.")
            try:
                expected = int(request.POST.get("version", ""))
            except ValueError as exc:
                raise SourceError("A valid source state version is required.") from exc
            controller.upload(file.name, file.read(), version(expected))
        else:
            payload = data(request)
            controller.command(payload.get("command"), payload.get("source"),
                               payload.get("example"), version(payload.get("version")))
        return response()
    except SourceError as exc:
        return response(str(exc), 400)
    except SourceConflict as exc:
        return response(str(exc), 409)
    except RequestDataTooBig:
        return response("Request exceeds the 2 MiB transport limit. The applied source is unchanged; shorten the editor text or correct the file.", 413)


@require_POST
def action(request):
    """Guard tool entry now; later steps will connect the language adapter here."""
    try:
        payload = data(request)
        if payload.get("operation") not in ("lint", "interpret", "typecheck", "compile", "execute"):
            raise SourceError("Unknown tool action.")
        source_model.require_applied_source(version(payload.get("version")))
        return response("This tool action is not available yet.", 501)
    except SourceError as exc:
        return response(str(exc), 400)
    except SourceConflict as exc:
        return response(str(exc), 409)
    except RequestDataTooBig:
        return response("Request exceeds the 2 MiB transport limit.", 413)
