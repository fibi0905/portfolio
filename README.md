# Portfolio — Fabio Nicolosi

Sito statico (Nginx) con una piccola API Python per il form contatti. Nessun database. Tutti i contenuti sono in `content/`.

```
content/
  site.json          dati personali, link, competenze
  projects.json      elenco progetti
  assets/
    foto.jpg         foto profilo
    cv.pdf           CV scaricabile
    projects/        immagini dei progetti
site/                codice del sito (HTML, CSS, JS)
api/                 invio email del form
nginx/               configurazione del container web
deploy/              configurazione del reverse proxy
```

## Requisiti

- CT LXC su Proxmox (Debian 12 o Ubuntu 22.04+), 512 MB RAM, 2 GB disco
- Opzioni della CT: `nesting=1` e `keyctl=1` (Options → Features)
- Docker Engine con Compose v2
- Account SMTP per inviare le email (Gmail con "Password per le app")
- Reverse proxy Nginx già attivo (Raspberry Pi) e dominio con DNS configurato

## Installazione

Dentro la CT:

```bash
curl -fsSL https://get.docker.com | sh

git clone <URL-del-repository> portfolio   # oppure copia la cartella
cd portfolio
cp .env.example .env
nano .env
docker compose up -d --build
```

Verifica:

```bash
curl http://localhost:8080/healthz      # risposta: ok
```

## Configurazione

Modifica `.env`:

| Variabile | Descrizione |
|---|---|
| `WEB_PORT` | porta esposta dalla CT (default `8080`) |
| `SMTP_HOST`, `SMTP_PORT` | server SMTP (`smtp.gmail.com`, `587`; con `465` usa SSL) |
| `SMTP_USER`, `SMTP_PASS` | credenziali SMTP (Gmail: password per le app) |
| `MAIL_TO` | indirizzo che riceve i messaggi |
| `SUBJECT_PREFIX` | prefisso oggetto, default `[Portfolio]` |
| `RATE_LIMIT_MAX`, `RATE_LIMIT_WINDOW` | invii massimi per IP nella finestra (secondi) |

Le email arrivano con oggetto `[Portfolio] <oggetto>` e `Reply-To` impostato sul visitatore. Filtro Gmail: oggetto contiene `[Portfolio]`.

Dopo ogni modifica a `.env`: `docker compose up -d`.

## Aggiornamento dei contenuti

I file in `content/` sono montati nel container: le modifiche sono visibili subito, senza riavvio né rebuild.

- Dati personali, link, competenze: `content/site.json`
- Foto: sostituisci `content/assets/foto.jpg` (quadrata)
- CV: sostituisci `content/assets/cv.pdf`
- Numero di telefono (opzionale): compila `phone` in `site.json`; se vuoto non viene mostrato

## Aggiornamento dei progetti

Aggiungi un oggetto a `content/projects.json`. L'ordine del file è l'ordine di visualizzazione.

```json
{
  "name": "Nome progetto",
  "featured": false,
  "description": "Breve descrizione.",
  "technologies": ["Docker", "Nginx"],
  "languages": ["Python"],
  "repo": "https://github.com/fibi0905/nome-repo",
  "image": "/content/assets/projects/nome-repo.jpg"
}
```

- `featured: true` mostra il progetto nella Home (se più di uno, vale il primo)
- `image`: copia il file in `content/assets/projects/` (consigliato 1600×1000); se vuoto compare un segnaposto

## Deploy

1. Avvia i container nella CT (vedi Installazione) e annota l'IP della CT.
2. Sul Raspberry Pi copia `deploy/nginx-reverse-proxy.conf` in `/etc/nginx/conf.d/`, sostituendo `192.168.1.20` con l'IP della CT.
3. Emetti il certificato (`certbot certonly --nginx -d cloudnic.cv`) e ricarica Nginx:

```bash
nginx -t && nginx -s reload
```

Se il reverse proxy è Nginx Proxy Manager: nuovo Proxy Host verso `IP-CT:8080`, SSL con Let's Encrypt e "Force SSL".

Aggiornare il codice del sito:

```bash
git pull
docker compose up -d --build
```

Log e stato:

```bash
docker compose ps
docker compose logs -f api
```
