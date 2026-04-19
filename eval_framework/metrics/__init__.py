from eval_framework.metrics.base import MetricRegistry
from eval_framework.metrics.correctness import CorrectnessMetric
from eval_framework.metrics.efficiency import EfficiencyMetric
from eval_framework.metrics.groundedness import GroundednessMetric
from eval_framework.metrics.hard_assertions import HardAssertionsMetric
from eval_framework.metrics.safety import SafetyMetric
from eval_framework.metrics.tool_use import ToolUseMetric


def build_registry() -> MetricRegistry:
    registry = MetricRegistry()
    registry.register(HardAssertionsMetric())
    registry.register(CorrectnessMetric())
    registry.register(GroundednessMetric())
    registry.register(ToolUseMetric())
    registry.register(SafetyMetric())
    registry.register(EfficiencyMetric())
    return registry

