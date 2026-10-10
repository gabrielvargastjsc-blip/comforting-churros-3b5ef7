"""Fase 1 - coleta de metadados do DataJud (API Publica, TJSC) para SQLite.

Uso:
  DATAJUD_APIKEY='<chave publica da wiki do CNJ>' python3 coleta_datajud.py [--db tjsc.db] [--meta 400] [--areas publico,civil]

- Elasticsearch DSL com paginacao por search_after (sort @timestamp, como no exemplo da wiki do CNJ).
- Idempotente: chave primaria = id do DataJud; rodar de novo nao duplica (upsert).
- Checkpoint por area na tabela `checkpoint`: retoma de onde parou.
- Backoff exponencial em 429/5xx/erro de rede; throttle de 3-5 s entre requisicoes.
- User-agent identificavel. Nenhuma barreira de acesso e contornada: 401/403 encerram a execucao.
A chave publica fica em https://datajud-wiki.cnj.jus.br/api-publica/acesso (nao vai no codigo).
"""
import argparse, json, os, random, sqlite3, sys, time, urllib.error, urllib.request
from datetime import datetime, timezone

URL = "https://api-publica.datajud.cnj.jus.br/api_publica_tjsc/_search"
UA = "TJSC-QC-Research/0.1 (pesquisa forense de decisoes publicas; OAB/SC)"
PAGE = 100

# Areas = familias de orgao julgador do 2o grau (padrao definido na Fase 0).
FAMILIAS = ["Direito Público", "Direito Civil", "Direito Comercial", "Criminal"]
AREAS = {
    "publico":   {"must": ["Direito Público"]},
    "civil":     {"must": ["Direito Civil"]},
    "comercial": {"must": ["Direito Comercial"]},
    "criminal":  {"must": ["Criminal"]},
    "outros":    {"must_not": FAMILIAS},
}

SCHEMA = """
CREATE TABLE IF NOT EXISTS processos (
  id TEXT PRIMARY KEY,
  numero_processo TEXT NOT NULL,
  area TEXT NOT NULL,
  grau TEXT, classe_codigo INTEGER, classe_nome TEXT,
  orgao_codigo INTEGER, orgao_nome TEXT, municipio_ibge INTEGER,
  sistema TEXT, formato TEXT, nivel_sigilo INTEGER,
  data_ajuizamento TEXT, data_ultima_atualizacao TEXT,
  assuntos TEXT, n_movimentos INTEGER,
  raw_json TEXT NOT NULL,
  coletado_em TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_proc_area ON processos(area);
CREATE INDEX IF NOT EXISTS ix_proc_numero ON processos(numero_processo);
CREATE TABLE IF NOT EXISTS checkpoint (
  area TEXT PRIMARY KEY, search_after TEXT, coletados INTEGER, atualizado_em TEXT
);
CREATE TABLE IF NOT EXISTS log_requisicoes (
  ts TEXT, area TEXT, status INTEGER, n_hits INTEGER, detalhe TEXT
);
"""

def agora():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")

def query(area):
    cfg = AREAS[area]
    b = {"must": [{"match": {"grau": "G2"}}]}
    if cfg.get("must"):
        b["must"] += [{"match_phrase": {"orgaoJulgador.nome": t}} for t in cfg["must"]]
    if cfg.get("must_not"):
        b["must_not"] = [{"match_phrase": {"orgaoJulgador.nome": t}} for t in cfg["must_not"]]
    return {"bool": b}

def post(body, key, db, area, tentativas=7):
    data = json.dumps(body).encode()
    for i in range(tentativas):
        req = urllib.request.Request(URL, data=data, method="POST", headers={
            "Authorization": f"APIKey {key}", "Content-Type": "application/json", "User-Agent": UA})
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                out = json.load(r)
            db.execute("INSERT INTO log_requisicoes VALUES (?,?,?,?,?)",
                       (agora(), area, 200, len(out["hits"]["hits"]), ""))
            return out
        except urllib.error.HTTPError as e:
            db.execute("INSERT INTO log_requisicoes VALUES (?,?,?,?,?)",
                       (agora(), area, e.code, 0, e.read()[:300].decode("utf-8", "replace")))
            db.commit()
            if e.code in (401, 403):
                sys.exit(f"HTTP {e.code}: acesso negado. Parando sem tentar contornar.")
            if e.code not in (429, 500, 502, 503, 504):
                raise
        except (urllib.error.URLError, TimeoutError) as e:
            db.execute("INSERT INTO log_requisicoes VALUES (?,?,?,?,?)", (agora(), area, 0, 0, str(e)[:300]))
            db.commit()
        espera = min(300, 5 * 2 ** i) + random.uniform(0, 3)
        print(f"  [{area}] erro, nova tentativa em {espera:.0f}s", flush=True)
        time.sleep(espera)
    raise RuntimeError("DataJud indisponivel apos varias tentativas; rode de novo para retomar do checkpoint.")

def grava(db, area, hit):
    s = hit["_source"]
    o, c = s.get("orgaoJulgador") or {}, s.get("classe") or {}
    db.execute("""INSERT INTO processos VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
      ON CONFLICT(id) DO UPDATE SET raw_json=excluded.raw_json,
        data_ultima_atualizacao=excluded.data_ultima_atualizacao,
        n_movimentos=excluded.n_movimentos, coletado_em=excluded.coletado_em""", (
        s.get("id") or hit["_id"], s.get("numeroProcesso"), area, s.get("grau"),
        c.get("codigo"), c.get("nome"), o.get("codigo"), o.get("nome"), o.get("codigoMunicipioIBGE"),
        (s.get("sistema") or {}).get("nome"), (s.get("formato") or {}).get("nome"), s.get("nivelSigilo"),
        s.get("dataAjuizamento"), s.get("dataHoraUltimaAtualizacao"),
        json.dumps([a.get("nome") for a in s.get("assuntos") or [] if isinstance(a, dict)], ensure_ascii=False),
        len(s.get("movimentos") or []), json.dumps(s, ensure_ascii=False), agora()))

def coleta(db, area, meta, key):
    row = db.execute("SELECT search_after FROM checkpoint WHERE area=?", (area,)).fetchone()
    after = json.loads(row[0]) if row and row[0] else None
    n = db.execute("SELECT COUNT(*) FROM processos WHERE area=?", (area,)).fetchone()[0]
    print(f"[{area}] inicio: {n} ja no banco", flush=True)
    while n < meta:
        body = {"size": min(PAGE, meta - n), "query": query(area),
                "sort": [{"@timestamp": {"order": "asc"}}]}
        if after:
            body["search_after"] = after
        hits = post(body, key, db, area)["hits"]["hits"]
        if not hits:
            print(f"[{area}] fim dos resultados", flush=True)
            break
        for h in hits:
            grava(db, area, h)
        after = hits[-1]["sort"]
        n = db.execute("SELECT COUNT(*) FROM processos WHERE area=?", (area,)).fetchone()[0]
        db.execute("INSERT OR REPLACE INTO checkpoint VALUES (?,?,?,?)", (area, json.dumps(after), n, agora()))
        db.commit()
        print(f"[{area}] {n}/{meta}", flush=True)
        time.sleep(random.uniform(3, 5))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "tjsc.db"))
    ap.add_argument("--meta", type=int, default=400)
    ap.add_argument("--areas", default=",".join(AREAS))
    a = ap.parse_args()
    key = os.environ.get("DATAJUD_APIKEY") or sys.exit("Defina DATAJUD_APIKEY com a chave publica da wiki do CNJ.")
    db = sqlite3.connect(a.db)
    db.executescript(SCHEMA)
    for area in a.areas.split(","):
        coleta(db, area.strip(), a.meta, key)
    for area, n in db.execute("SELECT area, COUNT(*) FROM processos GROUP BY area"):
        print(f"{area}\t{n}")
    db.close()

if __name__ == "__main__":
    main()
