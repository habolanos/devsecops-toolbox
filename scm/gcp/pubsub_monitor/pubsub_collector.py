"""
PubSubCollector - Recopilador de datos de Google Cloud Pub/Sub

Módulo responsable de recopilar datos de múltiples proyectos GCP,
incluyendo topics, subscriptions y métricas de Cloud Monitoring.

Características:
- Soporte multi-proyecto
- Caché de 1 hora
- Recopilación paralela
- Manejo de errores robusto
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed

from google.cloud import pubsub_v1
from google.cloud.pubsub_v1.types import ListTopicsRequest, ListSubscriptionsRequest
from google.cloud import monitoring_v3
from google.api_core import exceptions
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn
from rich.panel import Panel
from rich.table import Table

console = Console()
logger = logging.getLogger(__name__)


class PubSubCollector:
    """Recopila datos de Pub/Sub de múltiples proyectos GCP."""

    def __init__(self, projects: List[str], cache_ttl_hours: int = 1):
        """
        Inicializa el collector.

        Args:
            projects: Lista de IDs de proyectos GCP
            cache_ttl_hours: TTL del caché en horas
        """
        self.projects = projects
        self.cache_ttl = timedelta(hours=cache_ttl_hours)
        self.cache = {}
        self.publisher_client = pubsub_v1.PublisherClient()
        self.subscriber_client = pubsub_v1.SubscriberClient()
        self.monitoring_client = monitoring_v3.QueryServiceClient()
        self.errors = []

    def collect_all_data(self) -> Dict:
        """
        Recopila todos los datos de todos los proyectos.

        Returns:
            Diccionario con datos de todos los proyectos
        """
        results = {
            "timestamp": datetime.now().isoformat(),
            "projects": {},
            "errors": []
        }

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            console=console
        ) as progress:
            task = progress.add_task(
                "[cyan]Recopilando datos de Pub/Sub...",
                total=len(self.projects)
            )

            with ThreadPoolExecutor(max_workers=5) as executor:
                futures = {
                    executor.submit(self._collect_project_data, project): project
                    for project in self.projects
                }

                for future in as_completed(futures):
                    project = futures[future]
                    try:
                        data = future.result()
                        results["projects"][project] = data
                    except Exception as e:
                        error_msg = f"Error en {project}: {str(e)}"
                        results["errors"].append(error_msg)
                        logger.error(error_msg)
                    finally:
                        progress.update(task, advance=1)

        return results

    def _collect_project_data(self, project_id: str) -> Dict:
        """
        Recopila datos de un proyecto específico.

        Args:
            project_id: ID del proyecto GCP

        Returns:
            Diccionario con datos del proyecto
        """
        cache_key = f"project_{project_id}"
        
        # Verificar caché
        if cache_key in self.cache:
            cached_data, timestamp = self.cache[cache_key]
            if datetime.now() - timestamp < self.cache_ttl:
                return cached_data

        try:
            topics = self._collect_topics(project_id)
            subscriptions = self._collect_subscriptions(project_id)
            metrics = self._collect_metrics(project_id)

            data = {
                "topics": topics,
                "subscriptions": subscriptions,
                "metrics": metrics,
                "collected_at": datetime.now().isoformat()
            }

            # Guardar en caché
            self.cache[cache_key] = (data, datetime.now())

            return data

        except Exception as e:
            logger.error(f"Error recopilando datos de {project_id}: {str(e)}")
            raise

    def _collect_topics(self, project_id: str) -> List[Dict]:
        """
        Recopila información de todos los topics.

        Args:
            project_id: ID del proyecto GCP

        Returns:
            Lista de topics con metadatos
        """
        topics = []

        try:
            project_path = f"projects/{project_id}"
            request = ListTopicsRequest(project=project_path)

            for topic in self.publisher_client.list_topics(request=request):
                topic_data = {
                    "name": topic.name,
                    "display_name": topic.name.split("/")[-1],
                    "message_retention_duration": topic.message_retention_duration.seconds if topic.message_retention_duration else None,
                    "labels": dict(topic.labels) if topic.labels else {},
                    "kms_key_name": topic.kms_key_name or None,
                    "created_at": datetime.now().isoformat()
                }
                topics.append(topic_data)

        except exceptions.PermissionDenied:
            logger.warning(f"Permiso denegado para listar topics en {project_id}")
        except Exception as e:
            logger.error(f"Error listando topics en {project_id}: {str(e)}")

        return topics

    def _collect_subscriptions(self, project_id: str) -> List[Dict]:
        """
        Recopila información de todas las subscriptions.

        Args:
            project_id: ID del proyecto GCP

        Returns:
            Lista de subscriptions con metadatos
        """
        subscriptions = []

        try:
            project_path = f"projects/{project_id}"
            request = ListSubscriptionsRequest(project=project_path)

            for subscription in self.subscriber_client.list_subscriptions(request=request):
                sub_data = {
                    "name": subscription.name,
                    "display_name": subscription.name.split("/")[-1],
                    "topic": subscription.topic,
                    "push_config": {
                        "push_endpoint": subscription.push_config.push_endpoint if subscription.push_config else None
                    } if subscription.push_config else None,
                    "ack_deadline_seconds": subscription.ack_deadline_seconds,
                    "message_retention_duration": subscription.message_retention_duration.seconds if subscription.message_retention_duration else None,
                    "dead_letter_policy": {
                        "dead_letter_topic": subscription.dead_letter_policy.dead_letter_topic if subscription.dead_letter_policy else None,
                        "max_delivery_attempts": subscription.dead_letter_policy.max_delivery_attempts if subscription.dead_letter_policy else None
                    } if subscription.dead_letter_policy else None,
                    "retry_policy": {
                        "min_backoff": subscription.retry_policy.min_backoff.seconds if subscription.retry_policy and subscription.retry_policy.min_backoff else None,
                        "max_backoff": subscription.retry_policy.max_backoff.seconds if subscription.retry_policy and subscription.retry_policy.max_backoff else None
                    } if subscription.retry_policy else None,
                    "created_at": datetime.now().isoformat()
                }
                subscriptions.append(sub_data)

        except exceptions.PermissionDenied:
            logger.warning(f"Permiso denegado para listar subscriptions en {project_id}")
        except Exception as e:
            logger.error(f"Error listando subscriptions en {project_id}: {str(e)}")

        return subscriptions

    def _collect_metrics(self, project_id: str) -> Dict:
        """
        Recopila métricas de Cloud Monitoring.

        Args:
            project_id: ID del proyecto GCP

        Returns:
            Diccionario con métricas
        """
        metrics = {}

        try:
            project_name = f"projects/{project_id}"

            # Métricas de Pub/Sub
            metric_queries = [
                "fetch pubsub_subscription | metric 'pubsub.googleapis.com/subscription/num_undelivered_messages'",
                "fetch pubsub_subscription | metric 'pubsub.googleapis.com/subscription/oldest_unacked_message_age'",
                "fetch pubsub_subscription | metric 'pubsub.googleapis.com/subscription/backlog_bytes'",
                "fetch pubsub_topic | metric 'pubsub.googleapis.com/topic/publish_message_operation_count'",
            ]

            for query in metric_queries:
                try:
                    request = monitoring_v3.QueryTimeSeriesRequest(
                        name=project_name,
                        query=query
                    )
                    result = self.monitoring_client.query_time_series(request=request)
                    
                    for time_series in result.time_series_data:
                        metric_name = query.split("'")[1]
                        metrics[metric_name] = {
                            "values": [point.values[0].double_value for point in time_series.point_data],
                            "timestamps": [point.time_interval.end_time.isoformat() for point in time_series.point_data]
                        }

                except Exception as e:
                    logger.debug(f"Error consultando métrica en {project_id}: {str(e)}")

        except exceptions.PermissionDenied:
            logger.warning(f"Permiso denegado para leer métricas en {project_id}")
        except Exception as e:
            logger.error(f"Error recopilando métricas de {project_id}: {str(e)}")

        return metrics

    def display_collection_summary(self, results: Dict) -> None:
        """
        Muestra resumen de recopilación.

        Args:
            results: Resultados de la recopilación
        """
        table = Table(title="📊 Resumen de Recopilación de Datos")
        table.add_column("Proyecto", style="cyan")
        table.add_column("Topics", justify="right", style="green")
        table.add_column("Subscriptions", justify="right", style="blue")
        table.add_column("Estado", style="yellow")

        for project, data in results["projects"].items():
            status = "✅" if data else "❌"
            topics_count = len(data.get("topics", []))
            subs_count = len(data.get("subscriptions", []))
            table.add_row(project, str(topics_count), str(subs_count), status)

        console.print(table)

        if results["errors"]:
            console.print(Panel(
                "\n".join(results["errors"]),
                title="⚠️ Errores",
                style="red"
            ))
