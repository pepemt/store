"""Utilidades para emitir eventos de progreso (thinking steps) desde los nodos"""

import time
import asyncio
from typing import Dict, Any, Optional
from contextlib import asynccontextmanager

from models import (
    AgentState,
    ThinkingStep,
    StepType,
    StepStatus,
    ProgressCallback
)


async def emit_progress(
    state: AgentState,
    step_type: StepType,
    status: StepStatus,
    title: str,
    description: str,
    details: Optional[Dict[str, Any]] = None,
    is_parallel: bool = False,
    parallel_group: Optional[str] = None,
    duration_ms: Optional[int] = None
) -> None:
    """
    Emite un evento de progreso si hay un callback configurado.

    Args:
        state: Estado del agente con el callback
        step_type: Tipo de paso (vision, classifier, etc.)
        status: Estado del paso (started, completed, error)
        title: Título corto para mostrar en UI
        description: Descripción detallada del paso
        details: Datos adicionales (ej: términos de búsqueda)
        is_parallel: Si es parte de operaciones paralelas
        parallel_group: ID del grupo paralelo
        duration_ms: Duración en ms (para pasos completados)
    """
    callback = state.get("progress_callback")
    if callback is None:
        return

    step = ThinkingStep(
        step_type=step_type,
        status=status,
        title=title,
        description=description,
        details=details,
        is_parallel=is_parallel,
        parallel_group=parallel_group,
        duration_ms=duration_ms
    )

    try:
        await callback(step)
    except Exception as e:
        # No queremos que errores en el callback rompan el flujo principal
        import logging
        logging.getLogger(__name__).warning(f"Error emitting progress: {e}")


@asynccontextmanager
async def track_step(
    state: AgentState,
    step_type: StepType,
    title: str,
    description_start: str,
    description_end: str = "",
    details: Optional[Dict[str, Any]] = None,
    is_parallel: bool = False,
    parallel_group: Optional[str] = None
):
    """
    Context manager para trackear un paso de principio a fin.

    Uso:
        async with track_step(state, StepType.VISION, "Analizando imagen", "Procesando imagen con IA..."):
            # código del paso
            pass
        # Automáticamente emite 'started' al entrar y 'completed' al salir

    Args:
        state: Estado del agente
        step_type: Tipo de paso
        title: Título corto
        description_start: Descripción al iniciar
        description_end: Descripción al completar (opcional, usa description_start si no se provee)
        details: Datos adicionales
        is_parallel: Si es paralelo
        parallel_group: Grupo paralelo
    """
    start_time = time.time()

    # Emitir evento de inicio
    await emit_progress(
        state=state,
        step_type=step_type,
        status=StepStatus.STARTED,
        title=title,
        description=description_start,
        details=details,
        is_parallel=is_parallel,
        parallel_group=parallel_group
    )

    error_occurred = None
    try:
        yield
    except Exception as e:
        error_occurred = e
        raise
    finally:
        duration_ms = int((time.time() - start_time) * 1000)

        if error_occurred:
            await emit_progress(
                state=state,
                step_type=step_type,
                status=StepStatus.ERROR,
                title=title,
                description=f"Error: {str(error_occurred)[:100]}",
                details=details,
                is_parallel=is_parallel,
                parallel_group=parallel_group,
                duration_ms=duration_ms
            )
        else:
            await emit_progress(
                state=state,
                step_type=step_type,
                status=StepStatus.COMPLETED,
                title=title,
                description=description_end or description_start,
                details=details,
                is_parallel=is_parallel,
                parallel_group=parallel_group,
                duration_ms=duration_ms
            )


async def emit_parallel_start(
    state: AgentState,
    parallel_group: str,
    title: str,
    description: str,
    steps: list[str]
) -> None:
    """
    Emite evento de inicio de operaciones paralelas.

    Args:
        state: Estado del agente
        parallel_group: ID del grupo (ej: "search_hybrid")
        title: Título del grupo
        description: Descripción
        steps: Lista de nombres de pasos que se ejecutarán en paralelo
    """
    await emit_progress(
        state=state,
        step_type=StepType.SEARCH_PARALLEL,
        status=StepStatus.STARTED,
        title=title,
        description=description,
        details={"parallel_steps": steps},
        is_parallel=True,
        parallel_group=parallel_group
    )


async def emit_parallel_end(
    state: AgentState,
    parallel_group: str,
    title: str,
    description: str,
    duration_ms: int
) -> None:
    """
    Emite evento de fin de operaciones paralelas.
    """
    await emit_progress(
        state=state,
        step_type=StepType.SEARCH_PARALLEL,
        status=StepStatus.COMPLETED,
        title=title,
        description=description,
        is_parallel=True,
        parallel_group=parallel_group,
        duration_ms=duration_ms
    )
