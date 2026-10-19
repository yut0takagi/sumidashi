from sumidashi import frameworks, globs
from sumidashi.checks.common import py_mutable_annotation, ts_mutable_collection
from sumidashi.checks.ddd_evt import judge
from sumidashi.graph import Graph
from sumidashi.layers import allowed, build_layer_map, estimate_layer
from sumidashi.model import Import, Module


def test_globs():
    assert globs.match("src/domain/a.ts", "src/domain/**")
    assert globs.match("src/domain/a.ts", "src/domain")
    assert globs.match("a/b/c.py", "**/c.py")
    assert globs.match(".github/x.yml", ".github/**")
    assert globs.match("src/a.ts", "src/*.{ts,tsx}")
    assert not globs.match("src/x/a.ts", "src/*.ts")


def test_layer_estimation():
    assert estimate_layer("src/domain/order.ts")[0] == "domain"
    assert estimate_layer("src/api/domain/order.ts")[0] == "domain"  # 強いキーワードが弱いものに勝つ
    assert estimate_layer("src/main.ts")[0] == "main"
    assert estimate_layer("src/infra/db.ts")[0] == "infrastructure"
    assert estimate_layer("src/entities/user.ts")[0] is None
    lm = build_layer_map(["src/domain/a.ts", "src/handlers/b.ts", "lib/x.ts"], {"lib/**": "shared"})
    assert lm.layer_of("lib/x.ts") == "shared" and lm.source == "config+estimated"
    assert lm.estimable
    assert not build_layer_map(["src/domain/a.ts"], {}).estimable


def test_allowed_table():
    assert allowed("domain", "shared") and not allowed("domain", "application")
    assert allowed("adapter", "infrastructure") and not allowed("application", "adapter")
    assert not allowed("shared", "domain")


def test_ledger():
    led = frameworks.Ledger(add=["acme-orm"], allow=["zod"])
    assert led.classify("@nestjs/common", "typescript") == "web"
    assert led.classify("node:fs", "typescript") == "io"
    assert led.classify("@aws-sdk/client-s3", "typescript") == "cloud"
    assert led.classify("django.db.models", "python") == "orm"
    assert led.classify("acme-orm", "typescript") == "orm"
    assert led.classify("zod", "typescript") == "allow"
    assert led.classify("left-pad", "typescript") is None


def test_collections():
    assert ts_mutable_collection("Order[]")
    assert ts_mutable_collection("Map<string, X> | undefined")
    assert not ts_mutable_collection("readonly Order[]")
    assert not ts_mutable_collection("ReadonlyArray<Order>")
    assert not ts_mutable_collection("[number, number]")
    assert py_mutable_annotation("list[int]")
    assert py_mutable_annotation("Optional[Dict[str, int]]")
    assert not py_mutable_annotation("tuple[int, ...]")


def test_event_names():
    assert judge("OrderPlaced")[0] is None
    assert judge("OrderPlacedEvent")[0] is None
    assert judge("PaymentSentV2Event")[0] is None
    assert judge("OrderCreate")[0] == "violation"
    assert judge("OrderCancellationEvent")[0] == "borderline"
    assert judge("ProductFeedEvent")[0] == "violation"  # Feed は過去分詞でない
    assert judge("URLChanged")[0] is None


def test_scc():
    def mod(path, *targets, type_only=False):
        m = Module(path=path, lang="typescript", lines=["x"] * 5)
        for i, t in enumerate(targets):
            m.imports.append(Import(line=i + 1, end_line=i + 1, specifier=t, kind="import",
                                    type_only=type_only, resolved=[t]))
        return m

    mods = {
        "a": mod("a", "b"),
        "b": mod("b", "c"),
        "c": mod("c", "a", type_only=True),
        "d": mod("d"),
    }
    g = Graph(mods)
    assert g.sccs() == [["a", "b", "c"]]
    assert g.sccs(include_type_only=False) == []
