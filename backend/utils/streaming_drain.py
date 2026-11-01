"""Track complete HTTP ASGI lifetimes without consuming or buffering responses."""


class StreamingDrainMiddleware:
    """Keep shared drain accounting until the downstream ASGI task terminates.

    Response headers are not completion. Awaiting the full application also
    retains background cleanup, send failures and disconnect/cancellation
    unwinding. The server's existing bounded shutdown policy remains separate.
    """

    def __init__(self, app, state):
        self.app = app
        self.state = state

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http':
            await self.app(scope, receive, send)
            return
        self.state['inflight'] = self.state.get('inflight', 0) + 1
        try:
            await self.app(scope, receive, send)
        finally:
            self.state['inflight'] -= 1
