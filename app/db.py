import json
import logging
import os
from datetime import date, timedelta
from pathlib import Path

import oracledb

from .utils import today_kst

logger = logging.getLogger(__name__)

oracledb.defaults.fetch_lobs = False  # CLOB 을 str/파싱된 값으로 바로 받기

SCHEMA_FILE = Path(__file__).resolve().parent.parent / "sql" / "schema.sql"

_pool = None


def pool():
    global _pool
    if _pool is None:
        _pool = oracledb.create_pool(
            user=os.environ["ORACLE_USER"],
            password=os.environ["ORACLE_PASSWORD"],
            dsn=os.getenv("ORACLE_DSN", "localhost:1521/XEPDB1"),
            min=1, max=4, increment=1,
        )
    return _pool


def ping():
    with pool().acquire() as con:
        cur = con.cursor()
        cur.execute("SELECT 1 FROM dual")
        cur.fetchone()
    return True


def init_schema():
    # schema.sql 한 문장씩 실행, 이미 있으면(ORA-00955) 넘어감
    ddl = SCHEMA_FILE.read_text(encoding="utf-8")
    with pool().acquire() as con:
        cur = con.cursor()
        for stmt in _statements(ddl):
            try:
                cur.execute(stmt)
            except oracledb.DatabaseError as exc:
                (err,) = exc.args
                if err.code == 955:
                    continue
                raise
        con.commit()


def _statements(sql_text):
    for raw in sql_text.split(";"):
        body = "\n".join(l for l in raw.splitlines() if not l.strip().startswith("--")).strip()
        if body:
            yield body


_MERGE_MENU = """
MERGE INTO LUNCH_MENU t
USING (SELECT :menu_date AS MENU_DATE FROM dual) s
   ON (t.MENU_DATE = s.MENU_DATE)
WHEN MATCHED THEN UPDATE SET
    MENU_HASH = :menu_hash, MENUS = :menus, AI_SUMMARY = :summary,
    ESTIMATED_CALORIES = :calories, TAGS = :tags,
    RECOMMENDATION = :recommendation, IMAGE_URL = :image_url
WHEN NOT MATCHED THEN INSERT
    (MENU_DATE, MENU_HASH, MENUS, AI_SUMMARY, ESTIMATED_CALORIES, TAGS, RECOMMENDATION, IMAGE_URL)
    VALUES (:menu_date, :menu_hash, :menus, :summary, :calories, :tags, :recommendation, :image_url)
"""


def upsert_menu(menu_date, menu_hash, menus, analysis, image_url):
    d = date.fromisoformat(menu_date) if isinstance(menu_date, str) else menu_date
    params = {
        "menu_date": d, "menu_hash": menu_hash,
        "menus": json.dumps(menus, ensure_ascii=False),
        "summary": analysis.get("summary"), "calories": analysis.get("calories"),
        "tags": json.dumps(analysis.get("tags") or [], ensure_ascii=False),
        "recommendation": analysis.get("recommendation"), "image_url": image_url,
    }
    with pool().acquire() as con:
        cur = con.cursor()
        cur.execute(_MERGE_MENU, params)
        # 통계 테이블은 해당 날짜만 지우고 다시 넣음 (재실행 안전)
        cur.execute("DELETE FROM MENU_ITEM WHERE MENU_DATE = :d", d=d)
        if menus:
            cur.executemany(
                "INSERT INTO MENU_ITEM (MENU_DATE, DISH_NAME) VALUES (:1, :2)",
                [(d, dish) for dish in menus],
            )
        con.commit()


def save_cached_image(menu_hash, image_url):
    with pool().acquire() as con:
        cur = con.cursor()
        cur.execute(
            """
            MERGE INTO MENU_IMAGE_CACHE t
            USING (SELECT :h AS MENU_HASH FROM dual) s ON (t.MENU_HASH = s.MENU_HASH)
            WHEN NOT MATCHED THEN INSERT (MENU_HASH, IMAGE_URL) VALUES (:h, :u)
            """,
            h=menu_hash, u=image_url,
        )
        con.commit()


def get_cached_image(menu_hash):
    with pool().acquire() as con:
        cur = con.cursor()
        cur.execute("SELECT IMAGE_URL FROM MENU_IMAGE_CACHE WHERE MENU_HASH = :h", h=menu_hash)
        row = cur.fetchone()
        return row[0] if row else None


_MENU_COLS = "MENU_DATE, MENUS, AI_SUMMARY, ESTIMATED_CALORIES, TAGS, RECOMMENDATION, IMAGE_URL"


def _as_list(value):
    # IS JSON 컬럼을 oracledb 가 list 로 줄 때도, str 로 줄 때도 있어서 둘 다 받음
    if not value:
        return []
    if isinstance(value, (list, dict)):
        return value
    return json.loads(value)


def _row_to_menu(row):
    menu_date, menus, summary, calories, tags, recommendation, image_url = row
    return {
        "date": menu_date.strftime("%Y-%m-%d"),
        "menus": _as_list(menus),
        "analysis": {"summary": summary, "calories": calories,
                     "tags": _as_list(tags), "recommendation": recommendation},
        "image_url": image_url,
    }


def get_today():
    with pool().acquire() as con:
        cur = con.cursor()
        cur.execute(f"SELECT {_MENU_COLS} FROM LUNCH_MENU WHERE MENU_DATE = :today", today=today_kst())
        row = cur.fetchone()
        return _row_to_menu(row) if row else None


def get_history(days=30):
    since = today_kst() - timedelta(days=days)
    with pool().acquire() as con:
        cur = con.cursor()
        cur.execute(
            f"SELECT {_MENU_COLS} FROM LUNCH_MENU WHERE MENU_DATE >= :since ORDER BY MENU_DATE DESC",
            since=since,
        )
        return [_row_to_menu(r) for r in cur.fetchall()]


def get_stats():
    with pool().acquire() as con:
        cur = con.cursor()
        cur.execute("SELECT COUNT(*) FROM LUNCH_MENU")
        total = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM MENU_IMAGE_CACHE")
        cached = cur.fetchone()[0]
        cur.execute(
            """
            SELECT DISH_NAME, COUNT(*) AS CNT FROM MENU_ITEM
            GROUP BY DISH_NAME ORDER BY CNT DESC, DISH_NAME FETCH FIRST 5 ROWS ONLY
            """
        )
        top = [{"dish": d, "count": c} for d, c in cur.fetchall()]
    return {"total_menus": total, "cached_images": cached, "top_dishes": top}
