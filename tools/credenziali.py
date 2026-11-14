"""Su quale account Cloudflare questo sito puo' essere scritto, e con quali credenziali.

PERCHE ESISTE. Su questa macchina il login di wrangler e' UNO SOLO, condiviso da
tutti i progetti, e si sposta fra aziende diverse. Il 2026-11-13 il deploy di
flysystem e' fallito con "Authentication error [code: 10000]" perche' wrangler
era loggato su un altro account: il token era valido, semplicemente non vedeva
il progetto.

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

IL DEPOSITO DELLA MACCHINA. Se la macchina tiene un token per ogni account
Cloudflare (~/.cf-accounts/accounts.json, voci con name, accountId, apiToken),
e una voce ha lo stesso accountId del file qui sopra, vale il token di quella
voce: un solo token per account da tenere aggiornato, e nel file qui basta
l'accountId. Senza quella voce vale l'apiToken del file, come prima.

Il valore del token non viene mai stampato, ne' da qui ne' da chi usa questo
modulo, e nemmeno l'id dell'account. Se serve dire qualcosa su di lui si dice
dove sta e che tipo e', mai quanto vale.
"""
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FILE = ROOT / "_private" / "cloudflare.json"
DEPOSITO = Path.home() / ".cf-accounts" / "accounts.json"


def dal_deposito(acc):
    """Il token dell'account acc dal deposito della macchina, o None."""
    try:
        d = json.loads(DEPOSITO.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return None
    for voce in d.get("accounts") or []:
        if voce.get("accountId") == acc and len(voce.get("apiToken") or "") >= 20:
            return voce["apiToken"]
    return None

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
    """(accountId, token, da dove viene il token), o None con le istruzioni gia' stampate."""
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

    acc = d.get("accountId", "")
    if len(acc) != 32 or any(c not in "0123456789abcdef" for c in acc.lower()):
        print("  accountId in %s non e' 32 cifre esadecimali" % FILE)
        return None
    tok = dal_deposito(acc)
    if tok:
        return acc, tok, "dal deposito dei token della macchina"
    tok = d.get("apiToken", "")
    if not tok or len(tok) < 20:
        print("  apiToken in %s manca o e' troppo corto per essere un token," % FILE)
        print("  e il deposito dei token della macchina non ha questo account")
        return None
    return acc, tok, "da _private/cloudflare.json"


def ambiente():
    """L'ambiente per il processo wrangler, o None.

    Le due variabili esistono SOLO nel figlio. Non si scrivono nell'ambiente di
    questo processo, cosi' nessun altro comando lanciato dopo le eredita per
    sbaglio e finisce a scrivere su un account che non era quello previsto.
    """
    cred = leggi()
    if cred is None:
        return None
    acc, tok, fonte = cred
    env = dict(os.environ)
    env["CLOUDFLARE_ACCOUNT_ID"] = acc
    env["CLOUDFLARE_API_TOKEN"] = tok
    # un login OAuth rimasto in giro avrebbe la precedenza su alcune versioni
    # di wrangler: si toglie dal figlio, cosi' vale solo il token qui sopra
    env.pop("CLOUDFLARE_API_KEY", None)
    env.pop("CLOUDFLARE_EMAIL", None)
    print("  account fissato da _private/cloudflare.json, token %s" % fonte)
    return env
