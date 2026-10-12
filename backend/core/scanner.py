"""Polite link scanner background task with automatic failover promotion."""

import os
import time
import random
import logging
import asyncio
import hashlib
import httpx
from urllib.parse import urlparse
from typing import List, Dict, Any, Optional, Tuple

from backend.config.settings import settings
from backend.config.yaml_handler import YAMLConfigHandler
from backend.config.models import GlobalConfig
from backend.core.db import db_manager
from backend.core.link_tester import verify_link_detailed
from backend.core.link_status import link_status_repo
from backend.core.personal_repository import PersonalPlaylistRepository
from backend.core.processor import DataProcessor
from backend.core.utils import StreamUtils
from backend.core.notifier import Notifier
from backend.core.pro_bridge import ProBridge

# Global scanner execution state map
scanner_state: Dict[str, Any] = {
    "is_testing": False,
    "abort_requested": False,
}


async def _dispatch_telemetry(results: List[Dict[str, Any]]) -> None:
    """Dispatches anonymized telemetry metrics to cloud ingress."""
    try:
        from backend import __version__
        from backend.config.settings import settings
        cloud_url = os.getenv("PLUVIRA_CLOUD_URL", settings.cloud_base_url).rstrip("/")
        endpoint = f"{cloud_url}/api/v1/telemetry/ingress"
        
        sanitized_metrics = []
        for res in results:
            if isinstance(res, dict):
                raw_url = res.get("url") or res.get("original_url", "")
                try:
                    fqdn = urlparse(raw_url).hostname or ""
                except Exception:
                    fqdn = ""
                
                if fqdn:
                    domain_hash = hashlib.sha256(fqdn.strip().lower().encode("utf-8")).hexdigest()
                    sanitized_metrics.append({
                        "domain_hash": domain_hash,
                        "status": res.get("status", "unchecked"),
                        "code": res.get("code", 0),
                        "latency_ms": res.get("latency_ms", 0),
                        "health_score": res.get("health_score", 0.0)
                    })
                
        if not sanitized_metrics:
            return

        payload = {
            "engine_metadata": {
                "core_version": __version__,
            },
            "sanitized_metrics": sanitized_metrics
        }
        
        async with httpx.AsyncClient(timeout=5.0) as client:
            await client.post(endpoint, json=payload)
    except Exception as e:
        logging.debug(f"Telemetry dispatch failed: {e}")

def resolve_link_test_delays(
    source_cfg: Optional[Any], global_config: Any
) -> Tuple[float, float]:
    """Resolves link test min_delay and max_delay prioritizing source settings over global."""
    if source_cfg and source_cfg.settings and source_cfg.settings.link_test_settings:
        return (
            source_cfg.settings.link_test_settings.min_delay,
            source_cfg.settings.link_test_settings.max_delay,
        )
    if global_config.settings and global_config.settings.link_test_settings:
        return (
            global_config.settings.link_test_settings.min_delay,
            global_config.settings.link_test_settings.max_delay,
        )
    return 1.5, 3.5


async def run_link_test_batch_task(items: List[Dict[str, Any]]) -> None:
    """Executes polite link testing task in background with automatic failover promotion and notifications.

    Args:
        items (List[Dict[str, Any]]): Items list with url, original_url, source, user_agent.
    """
    global scanner_state
    scanner_state["is_testing"] = True
    scanner_state["abort_requested"] = False

    if ProBridge.is_available():
        link_db_path = str(db_manager.get_db_path(link_status_repo.db_path))
        main_db_path = str(db_manager.get_db_path())
        pro_res = await ProBridge.execute(
            "batch-link-test",
            payload={
                "items": items,
                "link_status_db_path": link_db_path,
                "epg_db_path": link_db_path,
                "main_db_path": main_db_path,
            },
            timeout=300.0,
        )
        if pro_res and isinstance(pro_res, dict) and pro_res.get("status") == "success":
            logging.info("Batch link scanner executed via Pro Rust engine.")
            res_obj = pro_res.get("result") if isinstance(pro_res.get("result"), dict) else pro_res
            results = res_obj.get("results") or res_obj.get("items") or []
            if isinstance(results, list):
                for res_item in results:
                    if isinstance(res_item, dict):
                        orig_u = res_item.get("original_url") or res_item.get("url", "")
                        curr_u = res_item.get("url") or orig_u
                        st = res_item.get("status", "unchecked")
                        code = res_item.get("code", 0)
                        cors = res_item.get("cors_supported", False)
                        proxy = res_item.get("needs_proxy", False)
                        err_msg = res_item.get("error_message")
                        if orig_u:
                            link_status_repo.update_status(orig_u, st, code, cors_supported=cors, needs_proxy=proxy, error_message=err_msg)
                        if curr_u and curr_u != orig_u:
                            link_status_repo.update_status(curr_u, st, code, cors_supported=cors, needs_proxy=proxy, error_message=err_msg)
            personal_repo = PersonalPlaylistRepository(settings.data_dir)
            for res_item in results:
                if isinstance(res_item, dict):
                    orig_u = res_item.get("original_url") or res_item.get("url", "")
                    curr_u = res_item.get("url") or orig_u
                    st = res_item.get("status", "unchecked")
                    err_msg = res_item.get("error_message")
                    personal_repo.sync_slot_health(curr_u, orig_u, st, err_msg)
            
            asyncio.create_task(_dispatch_telemetry(results))
            scanner_state["is_testing"] = False
            return

    logging.info(f"Starting batch link test for {len(items)} channels...")
    start_time = time.time()

    new_ko_channels: List[str] = []
    recovered_channels: List[str] = []
    online_count = 0
    offline_count = 0
    source_stats: Dict[str, Dict[str, int]] = {}

    try:
        processor = DataProcessor()
        handler = YAMLConfigHandler()
        config = handler.load_config()
        notifier = Notifier.from_config(config)
        personal_repo = PersonalPlaylistRepository(settings.data_dir)

        processed_channels = {
            ch["original_url"]: ch
            for ch in processor.get_processed_channels(config=config, include_backups=True)
        }

        for i, item in enumerate(items):
            if scanner_state["abort_requested"]:
                logging.warning("Batch link test aborted by user signal.")
                break

            orig_url = item.get("original_url") or item.get("url", "")
            test_url = item.get("url", orig_url)
            source_name = item.get("source", "Unknown")

            ch_info = processed_channels.get(orig_url)
            ch_name = ch_info.get("name") if ch_info else test_url
            ua = item.get("user_agent") or (ch_info.get("user_agent") if ch_info else "Mozilla/5.0")

            prev_entry = link_status_repo.get_status(orig_url)
            prev_status = (prev_entry.status or "unchecked").lower()

            logging.info(f"[{i+1}/{len(items)}] Testing stream '{ch_name}' ({source_name})...")

            source_cfg = next((s for s in config.sources if s.name == source_name), None)
            min_delay, max_delay = resolve_link_test_delays(source_cfg, config)

            test_res = await verify_link_detailed(test_url, ua)
            status_str = test_res["status"]
            code = test_res["code"]
            cors_supported = test_res.get("cors_supported", False)
            needs_proxy = test_res.get("needs_proxy", False)

            link_status_repo.update_status(orig_url, status_str, code, cors_supported, needs_proxy)
            if test_url and test_url != orig_url:
                link_status_repo.update_status(test_url, status_str, code, cors_supported, needs_proxy)
            personal_repo.sync_slot_health(test_url, orig_url, status_str, test_res.get("error_message"))
            logging.info(f"[{i+1}/{len(items)}] Result for '{ch_name}': {status_str.upper()} (HTTP {code})")

            if status_str == "offline":
                from backend.core.channel_merge_repository import ChannelMergeRepository
                merge_repo = ChannelMergeRepository()
                for m_name, m_cfg in merge_repo.get_all().items():
                    if m_cfg.primary_stream and (m_cfg.primary_stream.url == orig_url or m_cfg.primary_stream.url == test_url):
                        if m_cfg.backup_streams:
                            new_primary = m_cfg.backup_streams[0]
                            m_cfg.backup_streams = m_cfg.backup_streams[1:] + [m_cfg.primary_stream]
                            m_cfg.primary_stream = new_primary
                            merge_repo.save_merge(m_cfg, master_name=m_name)
                            notifier.dispatch_event(
                                event_name="link_failover_triggered",
                                title="🔀 Pluvira: Stream Failover Triggered",
                                body=f"Primary stream for '{m_name}' failed. Promoted backup stream: {new_primary.url}",
                                severity="warning",
                            )

            if status_str == "offline" and prev_status == "online":
                new_ko_channels.append(ch_name)
                notifier.dispatch_event(
                    event_name="link_ko_detected",
                    title="🔴 Pluvira: Link KO Detected",
                    body=f"Channel '{ch_name}' went OFFLINE (HTTP {code}).\nSource: {source_name}\nURL: {test_url}",
                    severity="warning",
                )

            if status_str == "online" and prev_status == "offline":
                recovered_channels.append(ch_name)
                notifier.dispatch_event(
                    event_name="link_recovered",
                    title="🟢 Pluvira: Link Recovered",
                    body=f"Channel '{ch_name}' is back ONLINE (HTTP {code}).\nSource: {source_name}\nURL: {test_url}",
                    severity="info",
                )

            if test_res.get("has_redirects") and test_res.get("redirect_count", 0) > 0:
                notifier.dispatch_event(
                    event_name="suspicious_redirect_detected",
                    title="⚠️ Pluvira: Suspicious Redirect Chain",
                    body=f"Channel '{ch_name}' redirected {test_res['redirect_count']} time(s).\nURL: {test_url}\nFinal URL: {test_res['url']}",
                    severity="info",
                )

            if source_name not in source_stats:
                source_stats[source_name] = {"online": 0, "offline": 0, "total": 0}
            source_stats[source_name]["total"] += 1

            if status_str == "online":
                online_count += 1
                source_stats[source_name]["online"] += 1
            else:
                offline_count += 1
                source_stats[source_name]["offline"] += 1

            if i < len(items) - 1:
                delay = random.uniform(min_delay, max_delay)
                time.sleep(delay)

        elapsed = time.time() - start_time
        logging.info(f"Batch link test completed in {elapsed:.2f}s.")

        events = config.get_event_config()
        health_threshold = events.source_health_threshold_pct

        for src_name, stats in source_stats.items():
            tot = stats["total"]
            if tot > 0:
                health_pct = round((stats["online"] / tot * 100.0), 1)
                if health_pct < health_threshold:
                    notifier.dispatch_event(
                        event_name="source_unhealth_warning",
                        title="⚠️ Pluvira: Source Health Warning",
                        body=f"Source '{src_name}' link health dropped to {health_pct}% (Threshold: {health_threshold}%).",
                        severity="warning",
                    )

        notifier.send_link_test_report(
            total_tested=len(items),
            online_count=online_count,
            offline_count=offline_count,
            new_ko_channels=new_ko_channels,
            recovered_count=len(recovered_channels),
            elapsed_time=elapsed,
        )
        
        core_results = []
        for item in items:
            orig_url = item.get("original_url") or item.get("url", "")
            entry = link_status_repo.get_status(orig_url)
            core_results.append({
                "url": orig_url,
                "status": entry.status,
                "code": entry.code,
            })
        asyncio.create_task(_dispatch_telemetry(core_results))

    except Exception as e:
        logging.error(f"Batch link test failed: {e}")
    finally:
        scanner_state["is_testing"] = False
        scanner_state["abort_requested"] = False
