"""Execution middleware for EAG."""

from typing import Protocol, runtime_checkable

from eag.chief.intelligence.execution.models import ExecutionContext, ExecutionResult


@runtime_checkable
class ExecutionMiddleware(Protocol):
    """Protocol for execution middleware."""

    def before(self, context: ExecutionContext) -> ExecutionContext: ...
    def after(self, context: ExecutionContext, result: ExecutionResult) -> ExecutionResult: ...
    def error(self, context: ExecutionContext, error: Exception) -> Exception: ...


class LoggingMiddleware:
    """Simple logging middleware."""

    def before(self, context: ExecutionContext) -> ExecutionContext:
        print(
            f"[LOG] Starting execution {context.request_id} on {context.provider_id}/{context.model_id}"
        )
        return context

    def after(self, context: ExecutionContext, result: ExecutionResult) -> ExecutionResult:
        print(f"[LOG] Finished execution {context.request_id} with success={result.success}")
        return result

    def error(self, context: ExecutionContext, error: Exception) -> Exception:
        print(f"[LOG] Execution {context.request_id} failed: {error}")
        return error


class MetricsMiddleware:
    """Middleware for collecting metrics."""

    def __init__(self) -> None:
        self.success_count = 0
        self.failure_count = 0

    def before(self, context: ExecutionContext) -> ExecutionContext:
        return context

    def after(self, context: ExecutionContext, result: ExecutionResult) -> ExecutionResult:
        if result.success:
            self.success_count += 1
        else:
            self.failure_count += 1
        return result

    def error(self, context: ExecutionContext, error: Exception) -> Exception:
        self.failure_count += 1
        return error


class MiddlewarePipeline:
    """Composes multiple middleware into a single pipeline."""

    def __init__(self, middlewares: list[ExecutionMiddleware] | None = None) -> None:
        self._middlewares = middlewares or []

    def add(self, middleware: ExecutionMiddleware) -> None:
        self._middlewares.append(middleware)

    def execute(self, context: ExecutionContext, executor_func) -> ExecutionResult:
        ctx = context
        for m in self._middlewares:
            ctx = m.before(ctx)

        try:
            result = executor_func(ctx)
            for m in reversed(self._middlewares):
                result = m.after(ctx, result)
            return result
        except Exception as e:
            err = e
            for m in reversed(self._middlewares):
                err = m.error(ctx, err)
            raise err
