import time
from collections import defaultdict

from fastapi import HTTPException, Request, status


class InMemoryRateLimiter:
    """Limitador simples por IP, janela deslizante em memoria de processo.

    Adequado para uma unica instancia (caso do Render free tier). Se o app
    rodar em multiplas instancias, isso precisa migrar para um store
    compartilhado (Redis/Postgres).
    """

    def __init__(self, max_requests: int, window_seconds: int):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._hits: dict[str, list[float]] = defaultdict(list)

    def __call__(self, request: Request) -> None:
        client_ip = request.client.host if request.client else "unknown"
        now = time.monotonic()
        window_start = now - self.window_seconds

        hits = self._hits[client_ip]
        hits[:] = [t for t in hits if t > window_start]

        if len(hits) >= self.max_requests:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Muitas tentativas. Tente novamente em alguns minutos.",
            )

        hits.append(now)


# Login/registro: ate 10 tentativas por IP a cada 5 minutos.
auth_rate_limiter = InMemoryRateLimiter(max_requests=10, window_seconds=300)
