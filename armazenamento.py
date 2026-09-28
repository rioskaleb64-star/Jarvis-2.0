"""Agenda e memória locais. Cada operação usa sua própria conexão SQLite."""
from contextlib import contextmanager
from datetime import datetime, timedelta
import json
from pathlib import Path
import sqlite3
import threading
import time
import unicodedata


RAIZ = Path(__file__).resolve().parent


def normalizar_busca(texto):
    return "".join(c for c in unicodedata.normalize("NFD", str(texto).casefold()) if not unicodedata.combining(c))


def texto_valido(valor, campo, limite):
    if not isinstance(valor, str) or not valor.strip():
        raise ValueError(f"Informe {campo}.")
    valor = valor.strip()
    if len(valor) > limite:
        raise ValueError(f"{campo.capitalize()} deve ter até {limite} caracteres.")
    return valor


def interpretar_horario(quando, agora=None):
    """ISO com fuso, DD/MM/AAAA HH:MM, hoje/amanhã HH:MM ou próximo HH:MM."""
    agora = time.time() if agora is None else agora
    local = datetime.fromtimestamp(agora)
    texto = texto_valido(quando, "horário", 80).lower()
    if texto.startswith(("hoje ", "amanhã ", "amanha ")):
        dia, hora = texto.split(maxsplit=1)
        alvo = datetime.combine(local.date(), datetime.strptime(hora, "%H:%M").time())
        if dia != "hoje":
            alvo += timedelta(days=1)
    elif len(texto) == 5 and texto[2] == ":":
        alvo = datetime.combine(local.date(), datetime.strptime(texto, "%H:%M").time())
        if alvo.timestamp() <= agora:
            alvo += timedelta(days=1)
    else:
        try:
            alvo = datetime.fromisoformat(texto.replace("z", "+00:00"))
        except ValueError:
            try:
                alvo = datetime.strptime(texto, "%d/%m/%Y %H:%M")
            except ValueError as exc:
                raise ValueError("Use HH:MM, amanhã HH:MM ou DD/MM/AAAA HH:MM.") from exc
    segundos = alvo.timestamp()
    if segundos <= agora:
        raise ValueError("Esse horário já passou. Informe um horário futuro.")
    if segundos > agora + 366 * 86400:
        raise ValueError("Agende no máximo um ano à frente.")
    return segundos


def data_legivel(segundos):
    return datetime.fromtimestamp(segundos).strftime("%d/%m/%Y às %H:%M:%S")


class Agenda:
    def __init__(self, caminho=None):
        self.caminho = Path(caminho or RAIZ / "dados" / "jarvis.db")
        self.caminho.parent.mkdir(parents=True, exist_ok=True)
        with self.conexao() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS notas (
                    id INTEGER PRIMARY KEY, titulo TEXT NOT NULL, texto TEXT NOT NULL,
                    criado REAL NOT NULL, atualizado REAL NOT NULL);
                CREATE TABLE IF NOT EXISTS tarefas (
                    id INTEGER PRIMARY KEY, titulo TEXT NOT NULL,
                    estado TEXT NOT NULL DEFAULT 'pendente', criado REAL NOT NULL);
                CREATE TABLE IF NOT EXISTS lembretes (
                    id INTEGER PRIMARY KEY, texto TEXT NOT NULL, quando REAL NOT NULL,
                    estado TEXT NOT NULL DEFAULT 'pendente', grupo TEXT,
                    criado REAL NOT NULL);
                CREATE INDEX IF NOT EXISTS agenda_por_data ON lembretes(estado, quando);
                CREATE TABLE IF NOT EXISTS preferencias (
                    chave TEXT PRIMARY KEY, valor TEXT NOT NULL, atualizado REAL NOT NULL);
                CREATE TABLE IF NOT EXISTS configuracao (
                    chave TEXT PRIMARY KEY, valor TEXT NOT NULL);
            """)

    @contextmanager
    def conexao(self):
        db = sqlite3.connect(str(self.caminho), timeout=10)
        db.row_factory = sqlite3.Row
        db.create_function("normalizar", 1, normalizar_busca, deterministic=True)
        try:
            with db:
                yield db
        finally:
            db.close()

    def salvar_nota(self, titulo, texto):
        titulo = texto_valido(titulo, "título", 120)
        texto = texto_valido(texto, "texto", 12000)
        agora = time.time()
        with self.conexao() as db:
            return db.execute("INSERT INTO notas(titulo,texto,criado,atualizado) VALUES (?,?,?,?)",
                              (titulo, texto, agora, agora)).lastrowid

    def listar_notas(self, busca="", limite=30):
        busca = str(busca).strip()[:120]
        with self.conexao() as db:
            return [dict(r) for r in db.execute(
                "SELECT id,titulo,substr(texto,1,160) AS resumo,atualizado FROM notas "
                "WHERE instr(normalizar(titulo || ' ' || texto),normalizar(?))>0 ORDER BY atualizado DESC LIMIT ?",
                (busca, limite))]

    def ler_nota(self, identificador):
        with self.conexao() as db:
            linha = db.execute("SELECT * FROM notas WHERE id=?", (identificador,)).fetchone()
            if not linha:
                raise ValueError("Nota não encontrada.")
            return dict(linha)

    def adicionar_tarefa(self, titulo):
        with self.conexao() as db:
            return db.execute("INSERT INTO tarefas(titulo,criado) VALUES (?,?)",
                              (texto_valido(titulo, "tarefa", 300), time.time())).lastrowid

    def listar_tarefas(self, incluir_concluidas=False):
        with self.conexao() as db:
            return [dict(r) for r in db.execute(
                "SELECT * FROM tarefas WHERE estado='pendente' OR ? ORDER BY id DESC LIMIT 100",
                (int(incluir_concluidas),))]

    def definir_tarefa(self, identificador, concluida=True):
        with self.conexao() as db:
            alteradas = db.execute("UPDATE tarefas SET estado=? WHERE id=?",
                                  ("concluida" if concluida else "pendente", identificador)).rowcount
            if not alteradas:
                raise ValueError("Tarefa não encontrada.")

    def adicionar_lembretes(self, itens, grupo=None):
        agora = time.time()
        preparados = []
        for texto, quando in itens:
            texto = texto_valido(texto, "lembrete", 500)
            if not isinstance(quando, (float, int)) or not agora < quando <= agora + 366 * 86400:
                raise ValueError("Informe uma data futura dentro de um ano.")
            preparados.append((texto, quando, grupo, agora))
        with self.conexao() as db:
            return [db.execute("INSERT INTO lembretes(texto,quando,grupo,criado) VALUES (?,?,?,?)",
                               item).lastrowid for item in preparados]

    def listar_lembretes(self, incluir_encerrados=False):
        with self.conexao() as db:
            return [dict(r) for r in db.execute(
                "SELECT * FROM lembretes WHERE estado IN ('pendente','disparado') OR ? "
                "ORDER BY quando LIMIT 100", (int(incluir_encerrados),))]

    def alterar_lembrete(self, identificador, estado, minutos=None):
        if estado not in {"concluido", "cancelado", "pendente"}:
            raise ValueError("Estado de lembrete inválido.")
        with self.conexao() as db:
            if minutos is not None:
                if isinstance(minutos, bool) or not 0 < minutos <= 10080:
                    raise ValueError("Adie entre 1 e 10080 minutos.")
                cursor = db.execute("UPDATE lembretes SET estado='pendente',quando=? WHERE id=?",
                                    (time.time() + minutos * 60, identificador))
            else:
                cursor = db.execute("UPDATE lembretes SET estado=? WHERE id=?", (estado, identificador))
            if not cursor.rowcount:
                raise ValueError("Lembrete não encontrado.")

    def cancelar_grupo(self, grupo):
        with self.conexao() as db:
            return db.execute("UPDATE lembretes SET estado='cancelado' WHERE grupo=? "
                              "AND estado IN ('pendente','disparado')", (grupo,)).rowcount

    def disparar_vencidos(self, agora=None):
        """Reserva os avisos em transação; reinícios não repetem notificações."""
        with self.conexao() as db:
            db.execute("BEGIN IMMEDIATE")
            vencidos = [dict(r) for r in db.execute(
                "SELECT * FROM lembretes WHERE estado='pendente' AND quando<=? ORDER BY quando",
                (time.time() if agora is None else agora,))]
            db.executemany("UPDATE lembretes SET estado='disparado' WHERE id=?",
                           [(r["id"],) for r in vencidos])
            return vencidos

    def lembrar(self, chave, valor):
        chave = texto_valido(chave, "nome da preferência", 60).lower()
        valor = texto_valido(valor, "preferência", 500)
        with self.conexao() as db:
            existe = db.execute("SELECT 1 FROM preferencias WHERE chave=?", (chave,)).fetchone()
            total = db.execute("SELECT count(*) FROM preferencias").fetchone()[0]
            if not existe and total >= 40:
                raise ValueError("Limite de 40 preferências. Esqueça uma antes de adicionar outra.")
            db.execute("INSERT INTO preferencias VALUES (?,?,?) ON CONFLICT(chave) "
                       "DO UPDATE SET valor=excluded.valor,atualizado=excluded.atualizado",
                       (chave, valor, time.time()))

    def preferencias(self):
        with self.conexao() as db:
            return {r["chave"]: r["valor"] for r in db.execute("SELECT * FROM preferencias ORDER BY chave")}

    def esquecer(self, chave):
        with self.conexao() as db:
            return bool(db.execute("DELETE FROM preferencias WHERE chave=?", (chave.strip().lower(),)).rowcount)

    def configurar(self, chave, valor):
        with self.conexao() as db:
            db.execute("INSERT INTO configuracao VALUES (?,?) ON CONFLICT(chave) "
                       "DO UPDATE SET valor=excluded.valor", (chave, json.dumps(valor, ensure_ascii=False)))

    def configuracao(self, chave, padrao=None):
        with self.conexao() as db:
            linha = db.execute("SELECT valor FROM configuracao WHERE chave=?", (chave,)).fetchone()
            return json.loads(linha[0]) if linha else padrao

    def exportar(self, pasta=None):
        pasta = Path(pasta or RAIZ / "exportacoes")
        pasta.mkdir(parents=True, exist_ok=True)
        destino = pasta / f"agenda-{time.time_ns()}.json"
        # Uma única transação de leitura garante uma fotografia coerente dos dados.
        with self.conexao() as db:
            db.execute("BEGIN")
            dados = {tabela: [dict(r) for r in db.execute(f"SELECT * FROM {tabela}")]
                     for tabela in ("notas", "tarefas", "lembretes", "preferencias")}
        destino.write_text(json.dumps({"versao": 1, "dados": dados}, ensure_ascii=False, indent=2), encoding="utf-8")
        return str(destino)


_agenda = None
_lock = threading.Lock()


def obter_agenda():
    global _agenda
    with _lock:
        if _agenda is None:
            _agenda = Agenda()
        return _agenda
