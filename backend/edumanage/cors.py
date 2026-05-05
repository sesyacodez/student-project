"""Allow browser requests from another origin during local dev (vanilla frontend on :5500)."""


class DevCorsMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.method == "OPTIONS":
            from django.http import HttpResponse

            resp = HttpResponse(status=204)
            self._add_headers(resp)
            return resp

        response = self.get_response(request)
        self._add_headers(response)
        return response

    def _add_headers(self, response):
        response["Access-Control-Allow-Origin"] = "*"
        response["Access-Control-Allow-Methods"] = (
            "GET, POST, PUT, PATCH, DELETE, OPTIONS"
        )
        response["Access-Control-Allow-Headers"] = (
            "Authorization, Content-Type, X-Requested-With"
        )
        response["Access-Control-Max-Age"] = "86400"
