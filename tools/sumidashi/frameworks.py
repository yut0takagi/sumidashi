"""フレームワーク台帳。外部パッケージ・標準モジュールを、設計チェックで使う分類に振り分ける。

分類:
  web        Web フレームワーク（HTTP の入口）
  orm / db   ORM・DB ドライバ・データストアのクライアント
  http       HTTP クライアント
  cloud      クラウド・SaaS の SDK、メール送信
  messaging  キュー・メッセージング
  di         DI コンテナ
  ui         UI フレームワーク
  io         ファイル・プロセス・ネットワークを扱う標準モジュール
  validation 入力検証・シリアライズ（ドメインで使うと要確認）
  allow      ドメインで使ってよいユーティリティ

台帳にないパッケージは「不明」として扱い、指摘しない（誤検知を減らすため）。
"""

from __future__ import annotations

VIOLATING = ("web", "orm", "db", "http", "cloud", "messaging", "di", "ui", "io")

# 完全一致か、"名前/" で始まるもの（TypeScript）・"名前." で始まるもの（Python）に当たる。
_TS: dict[str, str] = {
    # web
    "express": "web", "fastify": "web", "koa": "web", "@koa/router": "web", "koa-router": "web",
    "hono": "web", "next": "web", "@nestjs/common": "web", "@nestjs/core": "web",
    "@nestjs/platform-express": "web", "@nestjs/platform-fastify": "web", "@hapi/hapi": "web",
    "restify": "web", "h3": "web", "elysia": "web", "@trpc/server": "web", "apollo-server": "web",
    "@apollo/server": "web", "aws-lambda": "web",
    # orm / db
    "typeorm": "orm", "@prisma/client": "orm", "prisma": "orm", "sequelize": "orm",
    "sequelize-typescript": "orm", "mongoose": "orm", "drizzle-orm": "orm", "@mikro-orm": "orm",
    "kysely": "orm", "objection": "orm", "knex": "orm", "@typegoose/typegoose": "orm",
    "mongodb": "db", "pg": "db", "postgres": "db", "mysql": "db", "mysql2": "db", "sqlite3": "db",
    "better-sqlite3": "db", "redis": "db", "ioredis": "db", "@supabase/supabase-js": "db",
    "@google-cloud/firestore": "db", "@google-cloud/bigquery": "db", "@google-cloud/spanner": "db",
    "firebase-admin": "db", "firebase": "db", "dynamoose": "db", "@planetscale/database": "db",
    "@neondatabase/serverless": "db",
    # http
    "axios": "http", "node-fetch": "http", "got": "http", "superagent": "http", "undici": "http",
    "ky": "http", "cross-fetch": "http", "isomorphic-fetch": "http",
    # cloud
    "aws-sdk": "cloud", "@aws-sdk": "cloud", "@google-cloud": "cloud", "@azure": "cloud",
    "stripe": "cloud", "twilio": "cloud", "@sendgrid": "cloud", "nodemailer": "cloud", "@slack": "cloud",
    "openai": "cloud", "@anthropic-ai/sdk": "cloud",
    # messaging
    "kafkajs": "messaging", "amqplib": "messaging", "bullmq": "messaging", "bull": "messaging",
    "@google-cloud/pubsub": "messaging", "nats": "messaging",
    # di
    "inversify": "di", "tsyringe": "di", "typedi": "di", "awilix": "di",
    # ui
    "react": "ui", "react-dom": "ui", "vue": "ui", "@angular": "ui", "svelte": "ui", "solid-js": "ui",
    # io（Node の標準モジュール）
    "fs": "io", "fs/promises": "io", "http": "io", "https": "io", "http2": "io", "net": "io",
    "dgram": "io", "child_process": "io", "cluster": "io", "worker_threads": "io", "dns": "io",
    "tls": "io", "readline": "io",
    # validation
    "zod": "validation", "yup": "validation", "joi": "validation", "class-validator": "validation",
    "class-transformer": "validation", "io-ts": "validation", "valibot": "validation", "ajv": "validation",
    "@sinclair/typebox": "validation",
    # allow
    "lodash": "allow", "lodash-es": "allow", "date-fns": "allow", "dayjs": "allow", "luxon": "allow",
    "decimal.js": "allow", "big.js": "allow", "bignumber.js": "allow", "uuid": "allow", "nanoid": "allow",
    "ramda": "allow", "fp-ts": "allow", "neverthrow": "allow", "immer": "allow", "rxjs": "allow",
    "ts-pattern": "allow", "effect": "allow", "path": "allow", "crypto": "allow", "util": "allow",
    "events": "allow", "assert": "allow",
}

_PY: dict[str, str] = {
    # web
    "fastapi": "web", "flask": "web", "django.http": "web", "django.views": "web",
    "django.shortcuts": "web", "django.urls": "web", "rest_framework": "web", "starlette": "web",
    "aiohttp.web": "web", "tornado": "web", "falcon": "web", "sanic": "web", "pyramid": "web",
    "bottle": "web", "quart": "web", "litestar": "web", "werkzeug": "web",
    # orm / db
    "sqlalchemy": "orm", "django.db": "orm", "peewee": "orm", "tortoise": "orm", "pony": "orm",
    "sqlmodel": "orm", "mongoengine": "orm", "beanie": "orm", "odmantic": "orm",
    "psycopg2": "db", "psycopg": "db", "pymysql": "db", "MySQLdb": "db", "asyncpg": "db",
    "aiomysql": "db", "aiosqlite": "db", "sqlite3": "db", "motor": "db", "pymongo": "db",
    "redis": "db", "google.cloud.firestore": "db", "google.cloud.bigquery": "db",
    "google.cloud.spanner": "db", "elasticsearch": "db", "cassandra": "db",
    # http
    "requests": "http", "httpx": "http", "aiohttp": "http", "urllib3": "http",
    "urllib.request": "http", "http.client": "http",
    # cloud
    "boto3": "cloud", "botocore": "cloud", "google.cloud": "cloud", "azure": "cloud",
    "stripe": "cloud", "twilio": "cloud", "sendgrid": "cloud", "slack_sdk": "cloud",
    "smtplib": "cloud", "openai": "cloud", "anthropic": "cloud",
    # messaging
    "celery": "messaging", "kombu": "messaging", "pika": "messaging", "kafka": "messaging",
    "confluent_kafka": "messaging", "google.cloud.pubsub": "messaging", "dramatiq": "messaging",
    "rq": "messaging",
    # di
    "injector": "di", "dependency_injector": "di", "punq": "di", "lagom": "di",
    # io
    "subprocess": "io", "socket": "io", "ftplib": "io", "shutil": "io", "socketserver": "io",
    "asyncio.subprocess": "io",
    # validation
    "pydantic": "validation", "marshmallow": "validation", "cerberus": "validation",
    "voluptuous": "validation",
    # allow
    "dataclasses": "allow", "decimal": "allow", "datetime": "allow", "uuid": "allow", "enum": "allow",
    "typing": "allow", "typing_extensions": "allow", "abc": "allow", "attrs": "allow", "attr": "allow",
    "functools": "allow", "itertools": "allow", "collections": "allow", "re": "allow", "math": "allow",
    "zoneinfo": "allow", "returns": "allow",
}


class Ledger:
    """設定の frameworks.add・frameworks.allow を反映した台帳。"""

    def __init__(self, add: list[str] | None = None, allow: list[str] | None = None):
        self._ts = dict(_TS)
        self._py = dict(_PY)
        for name in add or []:
            # "name" か "name:分類"。分類を省略したら orm 扱い（ドメインから使ってはいけないもの）
            pkg, _, cat = name.partition(":")
            self._ts[pkg] = cat or "orm"
            self._py[pkg] = cat or "orm"
        for name in allow or []:
            self._ts[name] = "allow"
            self._py[name] = "allow"

    def classify(self, module: str, lang: str) -> str | None:
        """モジュール名の分類。台帳になければ None。"""
        if lang == "typescript":
            name = module[5:] if module.startswith("node:") else module
            table, sep = self._ts, "/"
        else:
            name, table, sep = module, self._py, "."
        if name in table:
            return table[name]
        parts = name.split(sep)
        for i in range(len(parts) - 1, 0, -1):
            prefix = sep.join(parts[:i])
            if prefix in table:
                return table[prefix]
        return None

    def is_violating(self, category: str | None) -> bool:
        return category in VIOLATING


WEB_DI_ONLY = {"Injectable", "Inject", "Module", "Optional", "forwardRef", "Logger", "Global"}
"""Web フレームワークから import しても、HTTP の型ではない DI 用のデコレータ。"""
