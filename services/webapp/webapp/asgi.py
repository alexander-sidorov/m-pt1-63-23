from contextlib import asynccontextmanager
from typing import AsyncIterator
from typing import Callable
from typing import Dict
from typing import Generator
from typing import List
from typing import Optional

import asyncpg

from alpha import dirs
from alpha.logging import logger
from alpha.settings import Settings
from webapp.custom_types import DbSetting
from webapp.custom_types import HostPortT
from webapp.custom_types import PayloadT
from webapp.custom_types import RequestT
from webapp.custom_types import ScopeAsgiT
from webapp.custom_types import ScopeT

settings = Settings()


@asynccontextmanager
async def get_db_connection() -> AsyncIterator:
    conn: Optional[asyncpg.Connection] = None
    log = logger.bind(db=settings.DATABASE_URL)
    try:
        log.debug("attempt to connect to db")
        conn = await asyncpg.connect(settings.DATABASE_URL)
        yield conn
    except Exception:
        log.exception("database is not available")
        raise
    finally:
        log.debug("closing the connection")
        if conn is not None:
            await conn.close()


async def get_db_settings() -> List[DbSetting]:
    sql = """
        SELECT
            trim(short_desc || ' ' || coalesce(extra_desc, '')) as description,
            name,
            setting,
            unit
        FROM
            pg_settings
        ;
    """

    db_settings: List[DbSetting] = []

    try:
        logger.debug("get db settings", sql=sql)
        conn: asyncpg.Connection
        async with get_db_connection() as conn:
            stmt = await conn.prepare(sql)
            records = await stmt.fetch()

        db_settings = [DbSetting.parse_obj(rec) for rec in records]

    except (OSError, asyncpg.PostgresError) as err:
        logger.exception("db exception", err=err)

    return db_settings


def views() -> Generator[Callable, None, None]:
    names = {
        "alexander_sidorov",
        "chernousik_ilya",
        "dmitriy_zhdanovich",
        "egor_pyshny",
        "ilya_putrich",
        "maksim_berezovik",
        "nikita_harbatsevich",
        "prxfsk17",
        "sergei_butkevich",
        "vadim_zhurau",
        "victor_bushilo",
    }

    hw_path = dirs.DIR_APP / "hw"

    for pkg_dir in hw_path.glob("*"):
        if pkg_dir.name not in names:
            continue
        if not pkg_dir.is_dir():
            continue
        if not (pkg_dir / "__init__.py").is_file():
            continue
        if not (pkg_dir / "lesson03.py").is_file():
            continue
        lesson03 = importlib.import_module(f"hw.{pkg_dir.name}.lesson03")
        if not hasattr(lesson03, "view"):
            continue

        yield lesson03.view


async def application(scope: Dict, receive: Callable, send: Callable) -> None:
    if scope["type"] == "lifespan":  # pragma: no cover
        return

    path = scope["path"]

    log = logger.bind(path=path)

    if path.startswith("/e"):
        log.debug("here goes an error ...")
        print(1 / 0)  # noqa: T201

    request = await receive()
    log.debug("get request", request=request)

    await send(
        {
            "headers": [
                [b"content-type", b"application/json"],
            ],
            "status": 200,
            "type": "http.response.start",
        }
    )
    for view in views():
        payload = view(path)
        if payload is not None:
            break
    db_settings = []

    if path == "/~/alexander_sidorov":
        payload = "Hello from Alexander Sidorov"
    elif path == "/~/chernousik_ilya/":
        payload = "Hello from Ilya Chernousik"
    elif path == "/~/dmitriy_zhdanovich/":
        payload = "Hello from Dmitriy Zhdanovich23"
    elif path =="/~/egor_pyshny/":
        payload = "Hello from Egor Pyshny"
    elif path == "/~/ilya_putrich/":
        payload = "Hello from Ilya Putrich"
    elif path == "/~/maksim_berezovik":
        payload = "Hello from Maksim Berezovik"
    elif path == "/~/nikita_harbatsevich":
        payload = "Hello from Nikita Harbatsevich"
    elif path == "/~/prxfsk17/":
        payload = "Hello from Alexander Haiko"
    elif path == "/~/sergei_butkevich/":
        payload = "Hello from Sergei Butkevich"
    elif path == "/~/vadim_zhurau/":
        payload = "Hello from Vadim Zhurau"
    elif path == "/~/victor_bushido/":
        payload = "Hello from Victor Bushilo"

    else:
        payload = build_payload(scope, request, db_settings).json(sort_keys=True, indent=2)

    await send(
        {
            "body": payload.encode(),
            "type": "http.response.body",
        }
    )

    log.debug("response has been sent")


def build_payload(
    scope: Dict,
    request: Dict,
    db_settings: List[DbSetting],
) -> PayloadT:
    payload = PayloadT(
        db_settings=db_settings,
        request=RequestT(
            body=request["body"].decode(),
            more_body=request["more_body"],
            type=request["type"],
        ),
        scope=ScopeT(
            asgi=ScopeAsgiT.parse_obj(scope["asgi"]),
            client=HostPortT.parse_obj(
                dict(zip(["host", "port"], scope["client"]))
            ),
            headers={k.decode(): v.decode() for k, v in scope["headers"]},
            http_version=scope["http_version"],
            method=scope["method"],
            path=scope["path"],
            query_string=scope["query_string"].decode(),
            raw_path=scope["raw_path"].decode(),
            root_path=scope["root_path"],
            scheme=scope["scheme"],
            server=HostPortT.parse_obj(
                dict(zip(["host", "port"], scope["server"]))
            ),
            type=scope["type"],
        ),
    )

    return payload


if not settings.MODE_DEBUG and settings.SENTRY_DSN:
    import sentry_sdk
    from sentry_sdk.integrations.asgi import SentryAsgiMiddleware

    sentry_sdk.init(settings.SENTRY_DSN, traces_sample_rate=1.0)
    application = SentryAsgiMiddleware(application)
