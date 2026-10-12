"""SPA static assets mount helper module."""

import logging
from pathlib import Path
from typing import Optional
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles


def setup_spa_static_mount(app: FastAPI, custom_dist_path: Optional[Path] = None) -> bool:
    """Mounts frontend/dist static files directly onto root path for Svelte SPA fallback routing.

    Args:
        app (FastAPI): Target application instance.
        custom_dist_path (Optional[Path]): Override path to frontend dist directory.

    Returns:
        bool: True if mounted successfully, False if dist directory not found.
    """
    target_dist = custom_dist_path or Path("frontend/dist")
    if target_dist.exists() and target_dist.is_dir():
        app.mount("/", StaticFiles(directory=target_dist, html=True), name="spa_frontend")
        logging.info(f"Mounted SPA frontend static files directly from: {target_dist}")
        return True

    logging.warning("SPA frontend dist directory not found. Running in headless API-only mode.")
    return False
