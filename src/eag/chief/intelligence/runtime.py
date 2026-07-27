"""AI Intelligence runtime for EAG."""

from eag.events import EventBus
from eag.chief.intelligence.enums import RuntimeState
from eag.chief.intelligence.errors import NoMatchingModelError
from eag.chief.intelligence.events import SelectionCompleted, SelectionStarted
from eag.chief.intelligence.metrics import IntelligenceMetrics
from eag.chief.intelligence.models import ExecutionRequest, SelectionDecision
from eag.chief.intelligence.model_registry import ModelRegistry
from eag.chief.intelligence.provider_registry import ProviderRegistry
from eag.chief.intelligence.selector import ModelSelector


class IntelligenceRuntime:
    """Orchestrates AI model selection and routing."""
    
    def __init__(
        self,
        event_bus: EventBus,
        model_registry: ModelRegistry | None = None,
        provider_registry: ProviderRegistry | None = None,
        selector: ModelSelector | None = None
    ) -> None:
        self._event_bus = event_bus
        self._model_registry = model_registry or ModelRegistry()
        self._provider_registry = provider_registry or ProviderRegistry()
        self._selector = selector or ModelSelector()
        self._state = RuntimeState.UNINITIALIZED
        self._metrics = IntelligenceMetrics()

    @property
    def state(self) -> RuntimeState:
        return self._state

    @property
    def metrics(self) -> IntelligenceMetrics:
        return self._metrics

    @property
    def models(self) -> ModelRegistry:
        return self._model_registry

    @property
    def providers(self) -> ProviderRegistry:
        return self._provider_registry

    def initialize(self) -> None:
        if self._state == RuntimeState.UNINITIALIZED:
            self._state = RuntimeState.READY

    def select_model(self, request: ExecutionRequest) -> SelectionDecision:
        """Processes an execution request and returns a selection decision."""
        if self._state != RuntimeState.READY:
            raise RuntimeError("Runtime is not ready.")

        self._state = RuntimeState.SELECTING
        self._event_bus.publish(SelectionStarted(capability=request.capability))
        
        try:
            decision = self._selector.select(
                request,
                self._model_registry.available(),
                self._provider_registry.available()
            )
            self._state = RuntimeState.READY
            
            self._event_bus.publish(SelectionCompleted(
                model_id=decision.model.id,
                confidence=decision.confidence
            ))
            
            self._metrics = IntelligenceMetrics(
                registered_models=len(self._model_registry.list()),
                registered_providers=len(self._provider_registry.list()),
                selection_count=self._metrics.selection_count + 1,
                average_confidence=(self._metrics.average_confidence + decision.confidence) / 2
            )
            return decision
        except NoMatchingModelError as e:
            self._state = RuntimeState.FAILED
            self._event_bus.publish(SelectionCompleted(model_id="", confidence=0.0))
            raise