#!/usr/bin/env python3
"""Fase 1 - coleta de metadados do DataJud (TJSC, 2º grau) por área.

Versão do Mac (Meu Drive/tjsc/fase1/, testada contra a API em 02-03/10/2026), adaptada
para rodar também na nuvem: chave por DATAJUD_APIKEY, pasta base por TJSC_BASE e
agg_orgaos_G2.tsv regenerado pela própria API se faltar.

Só usa a biblioteca padrão. Idempotente: upsert por numeroProcesso e cursor
search_after salvo por área na tabela checkpoints.

Uso: python3 coleta_datajud.py [--alvo 400] [--reset-cursor]
"""
import argparse, json, os, re, sqlite3, sys, time, urllib.request, urllib.error
from datetime import datetime, timezone
from pathlib import Path

AQUI = Path(__file__).resolve().parent
BASE = Path(os.environ.get("TJSC_BASE") or AQUI.parent)     # Meu Drive/tjsc no Mac
DB = BASE / "tjsc.db"
WIKI = BASE / "fase0" / "datajud_acesso.html"
URL = "https://api-publica.datajud.cnj.jus.br/api_publica_tjsc/_search"
UA = "TJSC-QC-Research/0.1 (pesquisa forense de decisoes publicas; OAB/SC)"
PAUSA = 4          # base do backoff em erro
PAUSA_ENTRE = 4    # pausa entre páginas (--pausa)
PAGINA = 100
TENTATIVAS = 8

AREAS = ["publico", "civil", "comercial", "criminal"]
AGG = AQUI / "agg_orgaos_G2.tsv"   # nomes reais (terms agg, grau G2)
# Preferência por casos recentes do eproc já com tempo para julgamento.
JANELA = {"gte": "20210101000000", "lte": "20241231235959"}


def chave_publica():
    if os.environ.get("DATAJUD_APIKEY"):
        return os.environ["DATAJUD_APIKEY"]
    if not WIKI.exists():
        sys.exit("Defina DATAJUD_APIKEY (chave pública da wiki do CNJ) ou salve " + str(WIKI))
    txt = re.sub(r"<[^>]*>", " ", WIKI.read_text(encoding="utf-8", errors="replace"))
    m = re.search(r"Authorization: APIKey ([A-Za-z0-9=+/_-]+)", re.sub(r"\s+", " ", txt))
    if not m:
        sys.exit("chave pública não encontrada em " + str(WIKI))
    return m.group(1)


def classifica(nome):
    """Classificação local pelo nome (cobre nomes com acentuação corrompida)."""
    n = (nome or "").lower()
    if re.search(r"criminal", n): return "criminal"
    if re.search(r"comercial", n): return "comercial"
    if re.search(r"direito civil|n.cleo civil", n): return "civil"
    if re.search(r"direito p.{1,3}blico|n.cleo p.{1,3}blico", n): return "publico"
    return "outros"


def gera_agg(key):
    """Recria agg_orgaos_G2.tsv com uma agregação terms (uma requisição)."""
    corpo = {"size": 0, "query": {"bool": {"filter": [{"term": {"grau.keyword": "G2"}}]}},
             "aggs": {"o": {"terms": {"field": "orgaoJulgador.nome.keyword", "size": 1000}}}}
    b = post(key, corpo)["aggregations"]["o"]["buckets"]
    with AGG.open("w", encoding="utf-8") as f:
        f.write("doc_count\torgaoJulgador.nome\n")
        for x in b:
            f.write(f"{x['doc_count']}\t{x['key']}\n")
    print(f"  agg_orgaos_G2.tsv gerado: {len(b)} órgãos", flush=True)
    time.sleep(PAUSA_ENTRE)


def nomes_por_area():
    """Agrupa os nomes exatos de órgão (da agregação) por área via classifica()."""
    grupos = {a: [] for a in AREAS + ["outros"]}
    for linha in AGG.read_text(encoding="utf-8").splitlines()[1:]:
        nome = linha.split("\t", 1)[1]
        grupos[classifica(nome)].append(nome)
    return grupos


NOMES = None


def consulta(area):
    # terms em orgaoJulgador.nome.keyword é bem mais leve que match_phrase no campo text.
    global NOMES
    NOMES = NOMES or nomes_por_area()
    return {"bool": {"filter": [
        {"range": {"dataAjuizamento": JANELA}},
        {"terms": {"orgaoJulgador.nome.keyword": NOMES[area]}}]}}


def post(key, corpo):
    """POST com backoff exponencial; shards rejeitados (cluster sobrecarregado) contam como erro."""
    dados = json.dumps(corpo).encode()
    for tentativa in range(TENTATIVAS):
        req = urllib.request.Request(URL, data=dados, method="POST", headers={
            "Authorization": "APIKey " + key, "Content-Type": "application/json", "User-Agent": UA})
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                d = json.load(r)
            falhas = d.get("_shards", {}).get("failed", 0)
            if falhas == 0:
                return d
            motivo = f"{falhas} shard(s) falharam: " + str(d["_shards"]["failures"][0]["reason"].get("type"))
        except urllib.error.HTTPError as e:
            if e.code in (400, 401, 403):
                print("  erro definitivo:", e.code, e.read()[:300], file=sys.stderr)
                raise
            motivo = f"HTTP {e.code}"
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
            motivo = str(e)
        espera = min(PAUSA * 2 ** (tentativa + 1), 600)
        print(f"  {datetime.now():%H:%M:%S} {motivo}; nova tentativa em {espera}s", file=sys.stderr, flush=True)
        time.sleep(espera)
    raise RuntimeError(f"falhou após {TENTATIVAS} tentativas")


def prepara_db(con):
    con.executescript("""
    CREATE TABLE IF NOT EXISTS processos (
        numeroProcesso  TEXT PRIMARY KEY,
        grau            TEXT,
        orgao           TEXT,
        classe          TEXT,
        assuntos        TEXT,      -- JSON [{codigo,nome}]
        dataAjuizamento TEXT,      -- AAAAMMDDhhmmss (como no DataJud)
        area            TEXT,      -- publico|civil|comercial|criminal|outros
        json_bruto      TEXT,      -- _source completo
        coletado_em     TEXT       -- UTC ISO-8601
    );
    CREATE INDEX IF NOT EXISTS ix_processos_area ON processos(area);
    CREATE TABLE IF NOT EXISTS checkpoints (
        area         TEXT PRIMARY KEY,
        search_after TEXT,          -- JSON do último sort
        coletados    INTEGER,
        atualizado_em TEXT
    );""")


def coleta_area(con, key, area, alvo, reset):
    linha = con.execute("SELECT search_after FROM checkpoints WHERE area=?", (area,)).fetchone()
    cursor = None if (reset or not linha or not linha[0]) else json.loads(linha[0])
    na_area = lambda: con.execute("SELECT COUNT(*) FROM processos WHERE area=?", (area,)).fetchone()[0]
    buscados = 0
    # Com --reset-cursor refaz a coleta do início (prova de idempotência);
    # sem ele, só completa o que falta para o alvo.
    while (buscados < alvo) if reset else (na_area() < alvo):
        corpo = {"size": PAGINA, "query": consulta(area),
                 "sort": [{"dataAjuizamento": "desc"}, {"id.keyword": "asc"}]}
        if cursor:
            corpo["search_after"] = cursor
        r = post(key, corpo)
        hits = r["hits"]["hits"]
        if not hits:
            print(f"  {area}: sem mais resultados")
            break
        agora = datetime.now(timezone.utc).isoformat(timespec="seconds")
        for h in hits:
            s = h["_source"]
            org = (s.get("orgaoJulgador") or {}).get("nome")
            con.execute("""INSERT INTO processos VALUES (?,?,?,?,?,?,?,?,?)
                ON CONFLICT(numeroProcesso) DO UPDATE SET grau=excluded.grau, orgao=excluded.orgao,
                classe=excluded.classe, assuntos=excluded.assuntos, dataAjuizamento=excluded.dataAjuizamento,
                area=excluded.area, json_bruto=excluded.json_bruto, coletado_em=excluded.coletado_em""",
                (s["numeroProcesso"], s.get("grau"), org, (s.get("classe") or {}).get("nome"),
                 json.dumps(s.get("assuntos", []), ensure_ascii=False), s.get("dataAjuizamento"),
                 area,
                 json.dumps(s, ensure_ascii=False), agora))
        buscados += len(hits)
        cursor = hits[-1]["sort"]
        con.execute("INSERT OR REPLACE INTO checkpoints VALUES (?,?,?,?)",
                    (area, json.dumps(cursor), na_area(), agora))
        con.commit()
        print(f"  {datetime.now():%H:%M:%S} {area}: +{len(hits)} -> {na_area()} na área", flush=True)
        time.sleep(PAUSA_ENTRE)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--alvo", type=int, default=400)
    ap.add_argument("--reset-cursor", action="store_true")
    ap.add_argument("--pagina", type=int, default=PAGINA, help="processos por requisição")
    ap.add_argument("--pausa", type=float, default=PAUSA_ENTRE, help="segundos entre requisições")
    a = ap.parse_args()
    globals().update(PAGINA=a.pagina, PAUSA_ENTRE=a.pausa)
    key = chave_publica()
    if not AGG.exists():
        gera_agg(key)
    con = sqlite3.connect(DB)
    prepara_db(con)
    for area in AREAS + ["outros"]:
        coleta_area(con, key, area, a.alvo, a.reset_cursor)
    for area, n in con.execute("SELECT area, COUNT(*) FROM processos GROUP BY area ORDER BY area"):
        print(f"{area}\t{n}")
    print("total", con.execute("SELECT COUNT(*) FROM processos").fetchone()[0])


if __name__ == "__main__":
    main()
