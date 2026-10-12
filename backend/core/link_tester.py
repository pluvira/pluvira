"""Async stream link verification and redirect tracing module."""

import time
import httpx
from typing import Dict, Any, Tuple, List


async def verify_link_detailed(url: str, user_agent: str = "Mozilla/5.0") -> Dict[str, Any]:
    """Performs naive basic HTTP link check for Python Core.

    Args:
        url (str): Target stream endpoint URL.
        user_agent (str): User-Agent header string.

    Returns:
        Dict[str, Any]: Basic inspection payload with status and HTTP status code.
    """
    start_time = time.perf_counter()
    trace_logs: List[str] = [f"[0.000s] Initializing check for: {url}", f"[0.001s] User-Agent: {user_agent}"]

    try:
        headers = {
            "User-Agent": user_agent,
            "Accept": "*/*",
        }
        async with httpx.AsyncClient(headers=headers, timeout=10.0, verify=False, follow_redirects=True) as client:
            response = await client.get(url)

            redirect_history = response.history
            redirect_count = len(redirect_history)
            has_redirects = redirect_count > 0

            for idx, hop in enumerate(redirect_history):
                hop_elapsed = time.perf_counter() - start_time
                reason = getattr(hop, "reason_phrase", None) or str(hop.status_code)
                target_loc = hop.headers.get("location") or "unknown"
                trace_logs.append(
                    f"[{hop_elapsed:.3f}s] Hop #{idx + 1}: HTTP {hop.status_code} ({reason}) -> {target_loc}"
                )

            final_elapsed = time.perf_counter() - start_time
            final_url = str(response.url)
            status_str = "online" if 200 <= response.status_code < 400 else "offline"
            trace_logs.append(
                f"[{final_elapsed:.3f}s] Final Destination: HTTP {response.status_code} ({final_url})"
            )

            cors_hdr = ""
            headers_dict = getattr(response, "headers", {})
            if headers_dict and hasattr(headers_dict, "items"):
                for k, v in headers_dict.items():
                    if str(k).lower() == "access-control-allow-origin":
                        cors_hdr = str(v)
                        break

            cors_supported = bool(
                cors_hdr and (cors_hdr == "*" or "localhost" in cors_hdr or "http" in cors_hdr)
            )
            needs_proxy = bool(status_str == "online" and not cors_supported)

            return {
                "status": status_str,
                "code": response.status_code,
                "cors_supported": cors_supported,
                "needs_proxy": needs_proxy,
                "trace": trace_logs,
                "url": final_url,
                "has_redirects": has_redirects,
                "redirect_count": redirect_count,
            }
    except Exception as e:
        err_elapsed = time.perf_counter() - start_time
        response = getattr(e, "response", None)
        redirect_history = getattr(response, "history", []) if response else []
        redirect_count = len(redirect_history)
        has_redirects = redirect_count > 0

        for idx, hop in enumerate(redirect_history):
            hop_elapsed = time.perf_counter() - start_time
            reason = getattr(hop, "reason_phrase", None) or str(hop.status_code)
            target_loc = hop.headers.get("location") or "unknown"
            trace_logs.append(
                f"[{hop_elapsed:.3f}s] Hop #{idx + 1}: HTTP {hop.status_code} ({reason}) -> {target_loc}"
            )

        trace_logs.append(f"[{err_elapsed:.3f}s] Error during request: {e}")
        return {
            "status": "offline",
            "code": getattr(response, "status_code", 0) if response else 0,
            "cors_supported": False,
            "needs_proxy": False,
            "trace": trace_logs,
            "url": str(getattr(response, "url", url)) if response else url,
            "has_redirects": has_redirects,
            "redirect_count": redirect_count,
        }


async def verify_link(url: str, user_agent: str = "Mozilla/5.0") -> Tuple[str, int]:
    """Simple wrapper returning status and code.

    Args:
        url (str): Target stream URL.
        user_agent (str): User-Agent header.

    Returns:
        Tuple[str, int]: Tuple of status string ('online'/'offline') and HTTP status code.
    """
    res = await verify_link_detailed(url, user_agent)
    return res["status"], res["code"]
