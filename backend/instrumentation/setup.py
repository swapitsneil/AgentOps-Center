"""
OpenTelemetry instrumentation setup for AgentOps Center.
Configures TracerProvider, MeterProvider, and LoggingHandler
with OTLP export to SigNoz.
"""
import logging
import os
from opentelemetry import trace, metrics
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.sampling import ParentBased, TraceIdRatioBased
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.resources import Resource, SERVICE_NAME, SERVICE_VERSION
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.logging import LoggingInstrumentor
from openinference.instrumentation.langchain import LangChainInstrumentor

logger = logging.getLogger(__name__)

_tracer_provider: TracerProvider | None = None
_meter_provider: MeterProvider | None = None

def setup_telemetry() -> tuple[trace.Tracer, metrics.Meter]:
    """Initialize all OTel providers. Call once at app startup."""
    global _tracer_provider, _meter_provider
    
    endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317")
    service_name = os.getenv("OTEL_SERVICE_NAME", "agentops-center-backend")
    service_version = os.getenv("OTEL_SERVICE_VERSION", "0.1.0")
    insecure = os.getenv("OTEL_EXPORTER_OTLP_INSECURE", "true").lower() == "true"
    
    resource = Resource.create({
        SERVICE_NAME: service_name,
        SERVICE_VERSION: service_version,
        "deployment.environment": os.getenv("APP_ENV", "development"),
        "telemetry.sdk.name": "opentelemetry",
        "agentops.project": "agentops-center",
    })
    
    # --- Tracer Provider ---
    span_exporter = OTLPSpanExporter(
        endpoint=endpoint,
        insecure=insecure,
    )
    _tracer_provider = TracerProvider(
        resource=resource,
        sampler=ParentBased(root=TraceIdRatioBased(1.0)),  # 100% sampling for demo
    )
    _tracer_provider.add_span_processor(BatchSpanProcessor(span_exporter))
    trace.set_tracer_provider(_tracer_provider)
    
    # --- Meter Provider ---
    metric_exporter = OTLPMetricExporter(
        endpoint=endpoint,
        insecure=insecure,
    )
    reader = PeriodicExportingMetricReader(metric_exporter, export_interval_millis=5000)
    _meter_provider = MeterProvider(resource=resource, metric_readers=[reader])
    metrics.set_meter_provider(_meter_provider)
    
    # --- Auto-Instrumentation ---
    LoggingInstrumentor().instrument(set_logging_format=True)
    HTTPXClientInstrumentor().instrument()
    LangChainInstrumentor().instrument()  # instruments LangGraph too
    
    logger.info(f"OTel initialized: service={service_name}, endpoint={endpoint}")
    
    tracer = trace.get_tracer(service_name, service_version)
    meter = metrics.get_meter(service_name, service_version)
    return tracer, meter

def instrument_fastapi(app) -> None:
    """Attach FastAPI auto-instrumentation after app creation."""
    FastAPIInstrumentor.instrument_app(app)

def shutdown_telemetry() -> None:
    """Flush and shutdown providers on app exit."""
    if _tracer_provider:
        _tracer_provider.shutdown()
    if _meter_provider:
        _meter_provider.shutdown()
