"""Su quale account Cloudflare questo sito puo' essere scritto, e con quali credenziali.

PERCHE ESISTE. Su questa macchina il login di wrangler e' UNO SOLO, condiviso da
tutti i progetti, e si sposta fra aziende diverse. Il 2026-11-13 il deploy di
flysystem e' fallito con "Authentication error [code: 10000]" perche' wrangler
era loggato su un altro account: il token era valido, semplicemente non vedeva
il progetto. Lo stesso problema, e la stessa soluzione, stanno gia' in
Car/_tools/lib/account.mjs.

COSA FA. Legge le credenziali da un file ignorato da git e le passa a wrangler
SOLO nell'ambiente del processo figlio. Niente login interattivo, niente token
che un altro progetto puo' sovrascrivere, e l'account e' fissato: se le
credenziali puntano altrove il deploy si rifiuta PRIMA di caricare 150 MB, non
dopo.

IL FILE, che non entra mai in git:

    _private/cloudflare.json
    {
      "accountId": "<32 cifre esadecimali dell'account giusto>",
      "apiToken":  "<token API con permesso Cloudflare Pages: Edit>"
    }

Si crea una volta sola dal pannello Cloudflare, con l'account giusto:
My Profile -> API Tokens -> Create Token -> Create Custom Token,
permesso Account / Cloudflare Pages / Edit, risorsa quell'account solo.

Il valore del token non viene mai stampato, ne' da qui ne' da chi usa questo
modulo. Se serve dire qualcosa su di lui si dice dove sta e che tipo e', mai
quanto vale.
"""
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FILE = ROOT / "_private" / "cloudflare.json"

ISTRUZIONI = """
  Manca %s

  Si crea una volta sola, e poi non serve piu' nessun login:

    1. Entra su dash.cloudflare.com CON L'ACCOUNT CHE POSSIEDE IL SITO.
       Non con un altro: e' esattamente l'errore che questo controllo evita.
    2. My Profile -> API Tokens -> Create Token -> Create Custom Token.
    3. Permissions: Account -> Cloudflare Pages -> Edit.
       Account Resources: solo quell'account.
    4. Copia il token e l'Account ID (sta nella pagina dell'account, 32 cifre
       esadecimali) dentro il file, cosi':

       {
         "accountId": "...",
         "apiToken":  "..."
       }

  Il file sta in una cartella ignorata da git e non viene mai pubblicato:
  pubblica.py copia solo assets/ e le pagine dichiarate.
"""


def leggi():
    """Le credenziali, o None con le istruzioni gia' stampate."""
    if not FILE.exists():
        print(ISTRUZIONI % FILE)
        return None
    try:
        # utf-8-sig e non utf-8: Set-Content -Encoding utf8 di PowerShell 5
        # scrive il BOM, e json.loads lo rifiuta con "Unexpected UTF-8 BOM".
        # utf-8-sig legge bene anche un file senza BOM, quindi copre i due casi.
        d = json.loads(FILE.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as e:
        print("  %s non e' JSON valido: %s" % (FILE, e))
        return None

    acc, tok = d.get("accountId", ""), d.get("apiToken", "")
    if len(acc) != 32 or any(c not in "0123456789abcdef" for c in acc.lower()):
        print("  accountId in %s non e' 32 cifre esadecimali" % FILE)
        return None
    if not tok or len(tok) < 20:
        print("  apiToken in %s manca o e' troppo corto per essere un token" % FILE)
        return None
    return acc, tok


def ambiente():
    """L'ambiente per il processo wrangler, o None.

    Le due variabili esistono SOLO nel figlio. Non si scrivono nell'ambiente di
    questo processo, cosi' nessun altro comando lanciato dopo le eredita per
    sbaglio e finisce a scrivere su un account che non era quello previsto.
    """
    cred = leggi()
    if cred is None:
        return None
    acc, tok = cred
    env = dict(os.environ)
    env["CLOUDFLARE_ACCOUNT_ID"] = acc
    env["CLOUDFLARE_API_TOKEN"] = tok
    # un login OAuth rimasto in giro avrebbe la precedenza su alcune versioni
    # di wrangler: si toglie dal figlio, cosi' vale solo il token qui sopra
    env.pop("CLOUDFLARE_API_KEY", None)
    env.pop("CLOUDFLARE_EMAIL", None)
    print("  credenziali da _private/cloudflare.json, account %s...%s" % (acc[:4], acc[-4:]))
    return env
