"""Service for safe persistence and loading of raw channel and EPG tables in SQLite."""

import time
import logging
import hashlib
from pathlib import Path
from typing import List, Dict, Any, Optional

import sqlite3
from datetime import datetime, timezone
from backend.core.parsers import XMLTVParser

from backend.config.settings import settings
from backend.core.db import db_manager


class RawDatabaseService:
    """Manages SQLite storage for raw channels, EPG index, and programmes in pluvira_epg.db."""

    def __init__(self, temp_dir: Optional[Path] = None, data_dir: Optional[Path] = None) -> None:
        """Initializes raw database file paths.

        Args:
            temp_dir (Optional[Path]): Override temporary RAM disk directory.
            data_dir (Optional[Path]): Override persistent data directory.
        """
        self._temp_dir = temp_dir
        self._data_dir = data_dir

    @property
    def temp_dir(self) -> Path:
        """Dynamically resolves temp directory."""
        if self._temp_dir is not None:
            return self._temp_dir
        return settings.temp_dir

    @property
    def data_dir(self) -> Path:
        """Dynamically resolves data directory."""
        if self._data_dir is not None:
            return self._data_dir
        return settings.data_dir




    @property
    def epg_db_path(self) -> Path:
        """Path to EPG SQLite database."""
        return self.data_dir / "pluvira_epg.db"

    def _get_epg_conn(self) -> sqlite3.Connection:
        """Opens SQLite connection and creates EPG tables and indexes."""
        conn = db_manager.get_connection(self.epg_db_path)
        with conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS epg_channels (
                    id TEXT PRIMARY KEY,
                    raw_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    source TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS epg_programmes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    channel_id TEXT NOT NULL,
                    start_utc TEXT NOT NULL,
                    stop_utc TEXT NOT NULL,
                    start_raw TEXT NOT NULL,
                    stop_raw TEXT NOT NULL,
                    title TEXT NOT NULL,
                    desc TEXT
                );
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_epg_prog_ch ON epg_programmes(channel_id);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_epg_prog_dates ON epg_programmes(start_utc, stop_utc);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_epg_prog_ch_start ON epg_programmes(channel_id, start_utc);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_epg_channels_raw ON epg_channels(raw_id);")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS raw_channels (
                    id TEXT PRIMARY KEY,
                    source TEXT NOT NULL,
                    name TEXT NOT NULL,
                    url TEXT NOT NULL,
                    original_url TEXT NOT NULL,
                    group_name TEXT,
                    logo TEXT,
                    tvg_id TEXT,
                    extinf TEXT
                );
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_raw_ch_source_name ON raw_channels(source, name);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_raw_ch_orig_url ON raw_channels(original_url);")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS processed_channels (
                    id TEXT PRIMARY KEY,
                    source TEXT NOT NULL,
                    name TEXT NOT NULL,
                    url TEXT NOT NULL,
                    original_url TEXT NOT NULL,
                    group_name TEXT,
                    logo TEXT,
                    tvg_id TEXT,
                    extinf TEXT,
                    user_agent TEXT,
                    force_proxy INTEGER DEFAULT 0,
                    is_modified INTEGER DEFAULT 0,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                );
                """
            )
            cursor = conn.execute("PRAGMA table_info(processed_channels);")
            columns = {row[1] for row in cursor.fetchall()}
            if "tvg_id" not in columns:
                conn.execute("ALTER TABLE processed_channels ADD COLUMN tvg_id TEXT;")
            if "extinf" not in columns:
                conn.execute("ALTER TABLE processed_channels ADD COLUMN extinf TEXT;")

            conn.execute("CREATE INDEX IF NOT EXISTS idx_proc_ch_source ON processed_channels(source);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_proc_ch_orig_url ON processed_channels(original_url);")
        return conn


    def load_existing_channels(self) -> List[Dict[str, Any]]:
        """Loads raw channels from SQLite raw_channels table.

        Returns:
            List[Dict[str, Any]]: Raw channel items list.
        """
        channels = []
        try:
            with self._get_epg_conn() as conn:
                cursor = conn.execute(
                    "SELECT source, name, url, original_url, group_name, logo, tvg_id, extinf FROM raw_channels"
                )
                for r in cursor.fetchall():
                    channels.append({
                        "s": r[0],
                        "n": r[1],
                        "u": r[2],
                        "orig_u": r[3],
                        "g": r[4] or "",
                        "l": r[5] or "",
                        "i": r[6] or "",
                        "x": r[7] or "",
                    })
        except Exception as e:
            logging.error(f"Failed to load raw channels from SQLite: {e}")

        return channels
    def load_existing_epg_index(self) -> Dict[str, str]:
        """Loads raw EPG index mapping from SQLite."""
        self.data_dir.mkdir(parents=True, exist_ok=True)

        epg_index = {}
        try:
            with self._get_epg_conn() as conn:
                cursor = conn.execute("SELECT id, name FROM epg_channels")
                for row in cursor.fetchall():
                    epg_index[row[0]] = row[1]
        except Exception as e:
            logging.error(f"Failed to load epg_index from SQLite: {e}")

        return epg_index

    def load_existing_raw_epg(
        self,
        channel_ids: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """Loads raw EPG schedules map from SQLite, optionally filtered by channel_ids."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        t0 = time.perf_counter()

        raw_epg: Dict[str, List[Dict[str, str]]] = {}
        try:
            with self._get_epg_conn() as conn:
                if channel_ids:
                    target_list = [str(cid).strip() for cid in channel_ids if cid and str(cid).strip()]
                    if not target_list:
                        return {}

                    search_id_map: Dict[str, List[str]] = {}
                    for cid in target_list:
                        search_id_map.setdefault(cid, []).append(cid)
                        if "::" in cid:
                            raw = cid.split("::", 1)[1]
                            search_id_map.setdefault(raw, []).append(cid)

                    all_candidates = list(search_id_map.keys())
                    for i in range(0, len(all_candidates), 500):
                        chunk = all_candidates[i : i + 500]
                        ph = ",".join("?" * len(chunk))
                        cur = conn.execute(
                            f"SELECT id, raw_id FROM epg_channels WHERE id IN ({ph}) OR raw_id IN ({ph})",
                            chunk + chunk,
                        )
                        for full_id, r_id in cur.fetchall():
                            if full_id in search_id_map:
                                for req in search_id_map[full_id]:
                                    search_id_map.setdefault(r_id, []).append(req)
                            if r_id in search_id_map:
                                for req in search_id_map[r_id]:
                                    search_id_map.setdefault(full_id, []).append(req)

                    all_db_ids = list(search_id_map.keys())
                    for i in range(0, len(all_db_ids), 500):
                        chunk = all_db_ids[i : i + 500]
                        ph = ",".join("?" * len(chunk))
                        cursor = conn.execute(
                            f"""
                            SELECT channel_id, COALESCE(NULLIF(start_raw, ''), start_utc),
                                   COALESCE(NULLIF(stop_raw, ''), stop_utc), title, desc
                            FROM epg_programmes
                            WHERE channel_id IN ({ph})
                            ORDER BY start_utc ASC
                            """,
                            chunk,
                        )
                        for row in cursor.fetchall():
                            db_ch_id = row[0]
                            prog_item = {
                                "s": row[1],
                                "e": row[2],
                                "t": row[3],
                                "d": row[4] or "",
                            }
                            matching_keys = set(search_id_map.get(db_ch_id, [db_ch_id]))
                            matching_keys.add(db_ch_id)
                            for k in matching_keys:
                                if k not in raw_epg:
                                    raw_epg[k] = []
                                raw_epg[k].append(prog_item)
                    elapsed_ms = (time.perf_counter() - t0) * 1000.0
                    tot_progs = sum(len(v) for v in raw_epg.values())
                    logging.info(
                        f"[EPG DB] Query by IDs completed in {elapsed_ms:.1f}ms: "
                        f"{len(raw_epg)} channels matched, {tot_progs} programmes found."
                    )
                    return raw_epg
                cursor = conn.execute(
                    "SELECT channel_id, COALESCE(NULLIF(start_raw, ''), start_utc), COALESCE(NULLIF(stop_raw, ''), stop_utc), title, desc FROM epg_programmes ORDER BY start_utc ASC"
                )
                for row in cursor.fetchall():
                    ch_id = row[0]
                    if ch_id not in raw_epg:
                        raw_epg[ch_id] = []
                    raw_epg[ch_id].append({
                        "s": row[1],
                        "e": row[2],
                        "t": row[3],
                        "d": row[4] or "",
                    })
        except Exception as e:
            logging.error(f"Failed to load raw_epg from SQLite: {e}")

        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        tot_progs = sum(len(v) for v in raw_epg.values())
        logging.info(
            f"[EPG DB] Completed load_existing_raw_epg in {elapsed_ms:.1f}ms: "
            f"{len(raw_epg)} channels, {tot_progs} programmes."
        )
        return raw_epg

    def _save_epg_channels_index(self, epg_index: Dict[str, str], now_str: str) -> None:
        """Saves or updates epg_channels table index in SQLite."""
        ch_rows = []
        for namespaced_id, name in epg_index.items():
            if "::" in namespaced_id:
                src, raw_id = namespaced_id.split("::", 1)
            else:
                src, raw_id = "Unknown", namespaced_id
            ch_rows.append((namespaced_id, raw_id, name or raw_id, src, now_str))

        if ch_rows:
            with self._get_epg_conn() as conn:
                with conn:
                    conn.executemany(
                        """
                        INSERT OR REPLACE INTO epg_channels (id, raw_id, name, source, updated_at)
                        VALUES (?, ?, ?, ?, ?)
                        """,
                        ch_rows,
                    )

    def save_epg_data_sqlite(
        self,
        epg_index: Dict[str, str],
        raw_epg: Dict[str, Any],
        clear_existing_sources: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Saves EPG channels index and programme schedules to SQLite database with Pro acceleration."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        from backend.core.pro_bridge import ProBridge
        if ProBridge.is_available() and raw_epg:
            epg_programs_payload = []
            for ch_id, progs in raw_epg.items():
                if isinstance(progs, list):
                    for p in progs:
                        if isinstance(p, dict) and p.get("s") and p.get("e"):
                            dt_s = XMLTVParser.parse_date(p["s"])
                            dt_e = XMLTVParser.parse_date(p["e"])
                            s_utc = (
                                dt_s.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
                                if dt_s
                                else p["s"]
                            )
                            e_utc = (
                                dt_e.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
                                if dt_e
                                else p["e"]
                            )
                            epg_programs_payload.append({
                                "channel_id": ch_id,
                                "title": p.get("t", ""),
                                "start_time": s_utc,
                                "stop_time": e_utc,
                                "description": p.get("d", ""),
                                "category": p.get("category", ""),
                                "icon": p.get("icon", ""),
                                "rating": p.get("rating", ""),
                                "start_raw": p.get("s", ""),
                                "stop_raw": p.get("e", ""),
                            })

            pro_res = ProBridge.execute_sync(
                "bulk-import-epg",
                payload={
                    "epg_db_path": str(self.epg_db_path),
                    "clear_existing_epg": bool(clear_existing_sources),
                    "target_sources": clear_existing_sources or [],
                    "epg_programs": epg_programs_payload,
                },
                timeout=60.0,
            )
            if pro_res and isinstance(pro_res, dict) and pro_res.get("status") == "success":
                self._save_epg_channels_index(epg_index, now_str)
                res_obj = pro_res.get("result") if isinstance(pro_res.get("result"), dict) else {}
                elapsed = res_obj.get("elapsed_ms", 0)
                imported = res_obj.get("imported_count", len(epg_programs_payload))
                logging.info(f"Pro Turbo EPG bulk-imported {imported} programmes in {elapsed}ms.")
                return {"engine": "pro", "elapsed_ms": elapsed, "imported_count": imported}

        start_db = time.perf_counter()
        try:
            with self._get_epg_conn() as conn:
                with conn:
                    if clear_existing_sources:
                        for src in clear_existing_sources:
                            prefix = f"{src}::%"
                            conn.execute(
                                """
                                DELETE FROM epg_programmes
                                WHERE channel_id LIKE ?
                                   OR channel_id IN (SELECT raw_id FROM epg_channels WHERE source = ?)
                                """,
                                (prefix, src),
                            )
                            conn.execute("DELETE FROM epg_channels WHERE source = ? OR id LIKE ?", (src, prefix))
                    elif raw_epg:
                        ch_ids = list(raw_epg.keys())
                        for i in range(0, len(ch_ids), 500):
                            chunk = ch_ids[i : i + 500]
                            placeholders = ",".join("?" * len(chunk))
                            conn.execute(f"DELETE FROM epg_programmes WHERE channel_id IN ({placeholders})", chunk)

                    ch_rows = []
                    for namespaced_id, name in epg_index.items():
                        if "::" in namespaced_id:
                            src, raw_id = namespaced_id.split("::", 1)
                        else:
                            src, raw_id = "Unknown", namespaced_id
                        ch_rows.append((namespaced_id, raw_id, name or raw_id, src, now_str))

                    if ch_rows:
                        conn.executemany(
                            """
                            INSERT OR REPLACE INTO epg_channels (id, raw_id, name, source, updated_at)
                            VALUES (?, ?, ?, ?, ?)
                            """,
                            ch_rows,
                        )

                    prog_rows = []
                    for ch_id, progs in raw_epg.items():
                        if isinstance(progs, list):
                            for p in progs:
                                if isinstance(p, dict) and p.get("s") and p.get("e"):
                                    s_raw = p["s"]
                                    e_raw = p["e"]
                                    dt_s = XMLTVParser.parse_date(s_raw)
                                    dt_e = XMLTVParser.parse_date(e_raw)
                                    s_utc = (
                                        dt_s.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
                                        if dt_s
                                        else s_raw
                                    )
                                    e_utc = (
                                        dt_e.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
                                        if dt_e
                                        else e_raw
                                    )
                                    prog_rows.append((
                                        ch_id,
                                        s_utc,
                                        e_utc,
                                        s_raw,
                                        e_raw,
                                        p.get("t", ""),
                                        p.get("d", ""),
                                    ))

                    if prog_rows:
                        conn.executemany(
                            """
                            INSERT INTO epg_programmes (channel_id, start_utc, stop_utc, start_raw, stop_raw, title, desc)
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                            """,
                            prog_rows,
                        )

            elapsed_ms = int((time.perf_counter() - start_db) * 1000)
            return {"engine": "core", "elapsed_ms": elapsed_ms, "imported_count": len(prog_rows)}
        except Exception as e:
            logging.error(f"Failed to save EPG data to SQLite: {e}")
            return {"engine": "core", "elapsed_ms": 0, "imported_count": 0}


    def save_raw_channels_sqlite(
        self,
        raw_channels: List[Dict[str, Any]],
        clear_existing_sources: Optional[List[str]] = None,
    ) -> None:
        """Saves raw channels into raw_channels table in pluvira_epg.db."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        with self._get_epg_conn() as conn:
            with conn:
                if clear_existing_sources:
                    for src in clear_existing_sources:
                        conn.execute("DELETE FROM raw_channels WHERE source = ?", (src,))
                else:
                    conn.execute("DELETE FROM raw_channels")

                rows = []
                for ch in raw_channels:
                    s = ch.get("s", "")
                    n = ch.get("n", "")
                    u = ch.get("u", "")
                    orig_u = ch.get("orig_u") or u
                    g = ch.get("g", "")
                    l = ch.get("l", "")
                    i = ch.get("i", "")
                    x = ch.get("x", "")
                    cid = hashlib.md5(f"{s}{n}{orig_u}".encode()).hexdigest()
                    rows.append((cid, s, n, u, orig_u, g, l, i, x))

                if rows:
                    conn.executemany(
                        """
                        INSERT OR REPLACE INTO raw_channels
                        (id, source, name, url, original_url, group_name, logo, tvg_id, extinf)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        rows,
                    )

    def load_existing_processed_channels(self) -> List[Dict[str, Any]]:
        """Loads channels from SQLite processed_channels table in pluvira_epg.db."""
        channels = []
        try:
            with self._get_epg_conn() as conn:
                cursor = conn.execute(
                    "SELECT id, source, name, url, original_url, group_name, logo, tvg_id, extinf, user_agent, force_proxy, is_modified FROM processed_channels"
                )
                for r in cursor.fetchall():
                    channels.append({
                        "id": r[0],
                        "source": r[1],
                        "name": r[2],
                        "url": r[3],
                        "original_url": r[4],
                        "group_name": r[5] or "",
                        "logo": r[6] or "",
                        "tvg_id": r[7] or "",
                        "extinf": r[8] or "",
                        "user_agent": r[9] or "",
                        "force_proxy": bool(r[10]),
                        "is_modified": bool(r[11]),
                    })
        except Exception as e:
            logging.error(f"Failed to load processed channels from SQLite: {e}")
        return channels

    def clear_processed_channels(self) -> None:
        """Truncates processed_channels table in pluvira_epg.db."""
        try:
            with self._get_epg_conn() as conn:
                with conn:
                    conn.execute("DELETE FROM processed_channels")
        except Exception as e:
            logging.error(f"Failed to clear processed channels in SQLite: {e}")

    def save_raw_database(
        self,
        raw_channels: List[Dict[str, Any]],
        epg_index: Dict[str, str],
        raw_epg: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """Persists raw channels and EPG data directly to pluvira_epg.db."""
        self.save_raw_channels_sqlite(raw_channels)
        return self.save_epg_data_sqlite(epg_index, raw_epg)
