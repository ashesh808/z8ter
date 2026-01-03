from z8ter.page import Page

from z8ter.requests import Request
from z8ter.responses import Response


class About(Page):
    async def get(self, request: Request) -> Response:
        return self.render(request, "about.jinja", {})
