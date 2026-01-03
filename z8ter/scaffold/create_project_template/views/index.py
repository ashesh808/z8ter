from z8ter.page import Page

from z8ter.requests import Request
from z8ter.responses import Response


class Index(Page):
    async def get(self, request: Request) -> Response:
        data = {"title": "Welcome to Z8ter!"}
        return self.render(request, "index.jinja", data)
