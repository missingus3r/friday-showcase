#!/usr/bin/env python3
"""Friday guardian — a Claude Code PreToolUse hook that blocks destructive commands.

Guardián de Friday (hook PreToolUse).

Revisa cada Bash / Edit / Write / NotebookEdit antes de que se ejecute y bloquea lo
destructivo o lo que toca archivos sensibles. Funciona aunque la sesión corra con
--dangerously-skip-permissions (los hooks se ejecutan igual).

Aprobación: al bloquear, le manda al dueño por el bot un código de 4 dígitos derivado
del comando exacto. Si el dueño responde "ok <código>" desde SU cuenta (lo registra el
ledger de Telethon como dir=out), el mismo comando pasa UNA vez dentro de 30 min.
Ni la sesión ni un prompt pueden autoaprobarse: el ledger, el estado del guardián y
este archivo están protegidos contra escritura.

Salida: exit 0 = permitir; exit 2 + stderr = bloquear (Claude Code le muestra el
motivo al modelo). Ante un error interno del propio guardián, permite y lo deja en
el log, para no dejar a Friday sin herramientas por un bug.
"""
import datetime as dt
import hashlib
import json
import os
import re
import shlex
import sys
import urllib.parse
import urllib.request

HOME = os.path.expanduser("~")
GDIR = os.path.join(HOME, ".claude/guard")
LOG = os.path.join(GDIR, "guard.log")
PENDING = os.path.join(GDIR, "pending.json")
USED = os.path.join(GDIR, "used.json")
LEDGER = os.path.join(HOME, ".claude/telegram-ledger.jsonl")
TOKEN_ENV = os.path.join(HOME, ".claude/channels/telegram/.env")
CHAT_ID = os.environ.get("GUARD_CHAT_ID", "")  # tu chat id de Telegram
WINDOW = dt.timedelta(minutes=30)

# Donde rm -r y find -delete están permitidos sin preguntar (temporales)
SAFE_PREFIXES = [
    os.path.join(HOME, "descargas-staging"),
    "/tmp/",
    os.path.join(HOME, ".cache"),
]
EXTERNAL = os.environ.get("GUARD_EXTERNAL", "/mnt/external")  # disco de datos que no se borra sin aprobación
# Archivos y carpetas que nadie escribe sin aprobación
PROTECTED = [
    os.path.join(HOME, ".ssh"),
    os.path.join(HOME, ".aws"),
    os.path.join(HOME, ".gnupg"),
    os.path.join(HOME, ".git-credentials"),
    os.path.join(HOME, ".claude/.env"),
    os.path.join(HOME, ".claude/channels/telegram/.env"),
    os.path.join(HOME, ".claude/settings.json"),
    os.path.join(HOME, ".claude/hooks"),
    GDIR,
    LEDGER,
]


def now():
    return dt.datetime.now(dt.timezone.utc)


def log(msg):
    try:
        os.makedirs(GDIR, exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as fh:
            fh.write(f"{now().isoformat(timespec='seconds')} {msg}\n")
    except Exception:
        pass


def load(path, default):
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return default


def save(path, data):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=1)
    os.replace(tmp, path)


def expand(p):
    p = p.strip("'\"")
    p = os.path.expandvars(os.path.expanduser(p))
    if "$" in p:
        # variable de shell sin resolver ($f, $S…): no se puede saber a dónde apunta;
        # no la resolvemos contra el cwd (daba falsos positivos si el cwd era ~/.claude/hooks)
        return "/__unresolved__/" + p
    if not os.path.isabs(p):
        p = os.path.normpath(os.path.join(os.getcwd(), p))
    return os.path.normpath(p)


def is_safe(path):
    return any(path == s.rstrip("/") or path.startswith(s.rstrip("/") + "/") for s in SAFE_PREFIXES)


def is_protected(path):
    return any(path == p or path.startswith(p + "/") for p in PROTECTED)


def mentions_protected(text):
    t = text.replace("~", HOME).replace("$HOME", HOME).replace("${HOME}", HOME)
    return any(p in t for p in PROTECTED) or ".git-credentials" in t or "/.ssh" in t or "/.aws" in t


HEREDOC = re.compile(r"<<-?\s*(['\"]?)(\w+)\1[^\n]*\n(.*?)\n[ \t]*\2[ \t]*(?=\n|$)", re.S)
WRITE_CODE = re.compile(r"open\([^)]*['\"][wax+]|write_text|write_bytes|writeFile|appendFile|shutil\.(move|copy|rmtree)|os\.(remove|unlink|rename|replace|rmdir)|\brm\s+-|>\s*~?/")


def segments(cmd):
    """Corta el comando en subcomandos por ; && || | y saltos de línea, sin cortar dentro de
    comillas. Los cuerpos de heredoc (texto o código pasado por stdin) no se leen como
    comandos: si un cuerpo nombra un archivo protegido y además escribe/borra, se agrega un
    subcomando sintético que la regla de scripts frena."""
    bodies = []

    def _cut(m):
        bodies.append(m.group(3))
        return m.group(0).split("\n", 1)[0]
    cmd = HEREDOC.sub(_cut, cmd)
    out, cur, q, i = [], [], None, 0
    while i < len(cmd):
        c = cmd[i]
        if q:
            cur.append(c)
            if c == q:
                q = None
        elif c in "'\"":
            q = c
            cur.append(c)
        elif cmd.startswith("&&", i) or cmd.startswith("||", i):
            out.append("".join(cur)); cur = []; i += 1
        elif c in ";|\n":
            out.append("".join(cur)); cur = []
        else:
            cur.append(c)
        i += 1
    out.append("".join(cur))
    segs = [s.strip() for s in out if s.strip()]
    for b in bodies:
        if mentions_protected(b) and WRITE_CODE.search(b):
            segs.append(f"python3 -c \"open('{PROTECTED[0]}/heredoc','w')\"")
        for line in b.splitlines():
            # líneas de shell dentro de un heredoc que se ejecuta con bash/sh
            if re.match(r"\s*(sudo|dd|mkfs|rm\s+-\w*[rR]|git\s+(reset\s+--hard|clean|push\s+-f|push\s+--force))\b", line):
                segs.append(line.strip())
    return segs


def tokens(seg):
    try:
        return shlex.split(seg, comments=False, posix=True)
    except ValueError:
        return seg.split()


def check_bash(cmd):
    """Devuelve el motivo del bloqueo o None."""
    for seg in segments(cmd):
        tk = tokens(seg)
        while tk and ("=" in tk[0] and not tk[0].startswith("-") and "/" not in tk[0].split("=")[0]):
            tk = tk[1:]  # VAR=valor delante del comando
        if not tk:
            continue
        prog = os.path.basename(tk[0])
        args = tk[1:]
        flags = [a for a in args if a.startswith("-")]
        paths = [a for a in args if not a.startswith("-")]

        if prog in ("sudo", "su", "doas"):
            return f"{prog}: ejecución como root"
        if prog in ("mkfs", "fdisk", "parted", "wipefs", "shred") or prog.startswith("mkfs."):
            return f"{prog}: operación sobre discos o borrado irrecuperable"
        if prog == "dd":
            return "dd: escritura cruda a disco"
        if prog in ("chmod", "chown", "chgrp") and any(f in ("-R", "--recursive") or (f.startswith("-") and not f.startswith("--") and "R" in f) for f in flags):
            return f"{prog} recursivo"
        if prog == "git" and args:
            sub = args[0]
            rest = args[1:]
            if sub == "reset" and "--hard" in rest:
                return "git reset --hard"
            if sub == "clean":
                return "git clean"
            if sub == "push" and any(a in ("-f", "--force", "--force-with-lease", "--mirror", "--delete", "-d") or a.startswith("+") or a.startswith("--force") for a in rest):
                return "git push forzado o que borra ramas"
            if sub in ("checkout", "restore") and ("." in rest or "--" in rest and rest[-1:] == ["."]):
                return f"git {sub} que descarta cambios locales"
        if prog in ("rm", "rmdir", "unlink"):
            recursive = any(f in ("-r", "-R", "--recursive") or (f.startswith("-") and not f.startswith("--") and ("r" in f or "R" in f)) for f in flags)
            if not paths:
                continue
            for p in paths:
                ap = expand(p)
                if ap in ("/", HOME, "/home", "/mnt", EXTERNAL) or p in ("*", ".", "..", "~", "/*"):
                    return f"rm sobre {p}"
                if ap.startswith(EXTERNAL):
                    return f"rm en el disco externo ({p})"
                if is_protected(ap):
                    return f"rm sobre archivo protegido ({p})"
                if recursive and not is_safe(ap):
                    return f"rm recursivo fuera de las carpetas temporales ({p})"
        if prog == "find" and ("-delete" in args or ("-exec" in args and any(a in ("rm", "shred") for a in args))):
            roots = [a for a in args[:args.index(next(a for a in args if a.startswith("-")))]] if any(a.startswith("-") for a in args) else args
            if not roots or not all(is_safe(expand(r)) for r in roots):
                return "find que borra fuera de las carpetas temporales"
        if prog == "mv" and paths:
            for p in paths[:-1]:
                ap = expand(p)
                if ap.startswith(EXTERNAL) or is_protected(ap):
                    return f"mv que saca o pisa algo del disco externo o protegido ({p})"
            dst = expand(paths[-1])
            if is_protected(dst):
                return f"mv sobre archivo protegido ({paths[-1]})"
        if prog in ("truncate",) and any(expand(p).startswith(EXTERNAL) or is_protected(expand(p)) for p in paths):
            return "truncate sobre archivo protegido o del disco externo"
        # Escrituras a archivos protegidos por redirección, tee, sed -i, cp, ln, etc.
        if mentions_protected(seg):
            redir = [expand(m) for m in re.findall(r"(?:^|[^<0-9&])\d?>>?\s*([^\s;&|]+)", seg)]
            if any(is_protected(r) for r in redir):
                return "escritura sobre archivo protegido (credenciales, settings, guardián o ledger)"
            if prog in ("tee", "cp", "install", "ln", "truncate", "chmod", "chown") and paths and any(is_protected(expand(p)) for p in (paths if prog in ("tee", "truncate", "chmod", "chown") else paths[-1:])):
                return "escritura sobre archivo protegido (credenciales, settings, guardián o ledger)"
            if prog in ("sed", "perl") and any(f.startswith("-i") or f == "-pi" for f in flags) and any(is_protected(expand(p)) for p in paths):
                return "escritura sobre archivo protegido (credenciales, settings, guardián o ledger)"
            # código inline (-c / -e) que abre en escritura o escribe un archivo protegido;
            # ejecutar un script protegido (p. ej. el guardián) no es escribirlo
            if prog in ("python3", "python", "node") and any(f in ("-c", "-e") for f in flags):
                if re.search(r"open\([^)]*['\"][wax+]|write_text|write_bytes|writeFile|appendFile|shutil\.(move|copy)|os\.(remove|unlink|rename|replace)", seg):
                    return "script que podría escribir un archivo protegido"
    return None


def check_file_tool(tool, inp):
    p = inp.get("file_path") or inp.get("notebook_path") or ""
    if p and is_protected(expand(p)):
        return f"{tool} sobre archivo protegido ({p})"
    if p and expand(p).startswith(EXTERNAL):
        return f"{tool} escribiendo en el disco externo ({p})"
    return None


def code_for(tool, payload):
    h = hashlib.sha256(f"{tool}\n{payload}".encode()).hexdigest()
    return h, str(int(h[:8], 16) % 9000 + 1000)


def approved(code, since):
    """¿El dueño respondió 'ok <code>' desde su cuenta después de 'since'? Devuelve el msg_id o None."""
    used = load(USED, {})
    try:
        with open(LEDGER, encoding="utf-8") as fh:
            lines = fh.readlines()[-400:]
    except Exception:
        return None
    pat = re.compile(rf"\bok\s*{code}\b", re.I)
    for line in reversed(lines):
        try:
            e = json.loads(line)
        except Exception:
            continue
        if e.get("dir") != "out" or not pat.search(e.get("text") or ""):
            continue
        ts = dt.datetime.fromisoformat(e["ts"])
        if ts < since or now() - ts > WINDOW:
            continue
        if str(e.get("msg_id")) in used:
            continue
        return e.get("msg_id")
    return None


def notify(text):
    try:
        tok = None
        with open(TOKEN_ENV, encoding="utf-8") as fh:
            for line in fh:
                if line.startswith("TELEGRAM_BOT_TOKEN="):
                    tok = line.split("=", 1)[1].strip().strip("'\"")
        if not tok or not CHAT_ID:
            return
        data = urllib.parse.urlencode({"chat_id": CHAT_ID, "text": text}).encode()
        urllib.request.urlopen(f"https://api.telegram.org/bot{tok}/sendMessage", data=data, timeout=10).read()
    except Exception as e:
        log(f"notify-error {e}")


def main():
    raw = sys.stdin.read()
    try:
        ev = json.loads(raw)
    except Exception:
        return 0
    tool = ev.get("tool_name", "")
    inp = ev.get("tool_input") or {}
    if tool == "Bash":
        payload = inp.get("command", "")
        reason = check_bash(payload)
    elif tool in ("Edit", "Write", "MultiEdit", "NotebookEdit"):
        payload = inp.get("file_path") or inp.get("notebook_path") or ""
        reason = check_file_tool(tool, inp)
    else:
        return 0
    if not reason:
        return 0

    h, code = code_for(tool, payload)
    pending = load(PENDING, {})
    first = pending.get(h)
    since = dt.datetime.fromisoformat(first["ts"]) if first else now()
    mid = approved(code, since) if first else None
    if mid is not None:
        used = load(USED, {})
        used[str(mid)] = {"code": code, "ts": now().isoformat(timespec="seconds")}
        save(USED, used)
        pending.pop(h, None)
        save(PENDING, pending)
        log(f"APROBADO code={code} msg={mid} {tool}: {payload[:300]}")
        return 0

    if os.environ.get("GUARD_DRY"):
        print(f"DRY BLOCK [{reason}] code={code}")
        return 2
    if not first or now() - dt.datetime.fromisoformat(first["ts"]) > WINDOW:
        pending[h] = {"code": code, "ts": now().isoformat(timespec="seconds"), "tool": tool, "payload": payload[:500], "reason": reason}
        save(PENDING, pending)
        # Explicación en castellano de qué haría: qué toca, cuánto pesa, si se puede deshacer
        def _size(p):
            try:
                if os.path.isfile(p):
                    return 1, os.path.getsize(p)
                n = s = 0
                for r, _, fs in os.walk(p):
                    for f in fs:
                        n += 1
                        try:
                            s += os.path.getsize(os.path.join(r, f))
                        except OSError:
                            pass
                    if n > 200000:
                        break
                return n, s
            except Exception:
                return 0, 0

        def _hum(b):
            for u in ("B", "KB", "MB", "GB", "TB"):
                if b < 1024:
                    return f"{b:.0f} {u}" if u == "B" else f"{b:.1f} {u}"
                b /= 1024
            return f"{b:.1f} PB"

        def _what(p):
            if not os.path.exists(p):
                return f"{p} (no existe hoy)"
            n, s = _size(p)
            kind = "carpeta" if os.path.isdir(p) else "archivo"
            return f"{kind} {p} ({n} archivo(s), {_hum(s)})"

        expl = []
        if tool == "Bash":
            for seg in segments(payload):
                tk = tokens(seg)
                if not tk:
                    continue
                prog = os.path.basename(tk[0])
                args = tk[1:]
                paths = [expand(a) for a in args if not a.startswith("-") and not a.startswith("/__unresolved__")]
                if prog in ("rm", "rmdir", "unlink"):
                    for p in paths:
                        expl.append(f"• Borraría {_what(p)}. No hay papelera: no se puede deshacer.")
                elif prog == "mv" and len(paths) >= 2:
                    for p in paths[:-1]:
                        expl.append(f"• Movería {_what(p)} a {paths[-1]}; si el destino existe, lo pisaría.")
                elif prog == "find" and ("-delete" in args or "-exec" in args):
                    roots = [p for p in paths if os.path.exists(p)]
                    expl.append("• Borraría los archivos que encuentre find dentro de: " + (", ".join(_what(r) for r in roots) or "(raíz no reconocida)") + ". No se puede deshacer.")
                elif prog == "git" and args:
                    sub = args[0]
                    if sub == "reset":
                        expl.append(f"• Descartaría todos los cambios sin commitear del repo en {os.getcwd()} (irreversible).")
                    elif sub == "clean":
                        expl.append(f"• Borraría los archivos no versionados del repo en {os.getcwd()} (irreversible).")
                    elif sub == "push":
                        expl.append("• Pisaría la historia o borraría ramas del repo remoto en GitHub; los commits pisados se pierden para los demás.")
                    elif sub in ("checkout", "restore"):
                        expl.append(f"• Descartaría los cambios locales sin commitear en {os.getcwd()}.")
                elif prog in ("sudo", "su", "doas"):
                    expl.append("• Ejecutaría como administrador: " + " ".join(args[:20]) + ". Con root puede tocar cualquier cosa del sistema.")
                elif prog in ("dd", "mkfs", "fdisk", "parted", "wipefs", "shred") or prog.startswith("mkfs."):
                    expl.append("• Escribiría directo sobre un disco o partición (o destruiría un archivo sin recuperación). Puede borrar todo lo que haya ahí.")
                elif prog in ("chmod", "chown", "chgrp"):
                    expl.append("• Cambiaría permisos o dueño de todo lo que hay bajo: " + ", ".join(_what(p) for p in paths if os.path.exists(p)) + ".")
                elif mentions_protected(seg):
                    expl.append("• Escribiría o modificaría un archivo protegido (credenciales, configuración de Friday, guardián o ledger).")
        else:
            p = expand(payload)
            expl.append(f"• {tool} modificaría {_what(p)}.")
        if not expl:
            expl.append(f"• Motivo: {reason}.")
        expl.append(f"• Carpeta de trabajo: {os.getcwd()}")
        notify(f"🛡️ Guardián: frené un comando de Friday ({reason}).\n\nQué haría:\n" + "\n".join(expl) +
               f"\n\nSi lo querés permitir una vez, respondé:  ok {code}\n(vale 30 min; si no respondés, no se ejecuta). El comando completo va abajo.")
        chunks = [payload[i:i + 3500] for i in range(0, len(payload), 3500)] or [""]
        for n, ch in enumerate(chunks, 1):
            notify(f"Comando completo ({tool}{f', parte {n}/{len(chunks)}' if len(chunks) > 1 else ''}):\n\n{ch}")
    log(f"BLOQUEADO code={code} {tool} [{reason}]: {payload[:300]}")
    sys.stderr.write(
        f"BLOQUEADO por el guardián de Friday: {reason}. Se pidió aprobación por Telegram con el código {code}. "
        f"No intentes rodearlo ni reformular el comando para esquivarlo. Si el dueño responde 'ok {code}', reintentá EXACTAMENTE el mismo comando dentro de 30 min.\n")
    return 2


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception as e:
        log(f"ERROR interno, se permite: {e!r}")
        sys.exit(0)
