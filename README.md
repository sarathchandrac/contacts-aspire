# Contacts platform (.NET Aspire)

An [Aspire](https://aspire.dev) app host that runs a small data platform locally:

| Service | Tech | What it does | Default address |
|---|---|---|---|
| `api` | FastAPI (Python) | `/contacts` from MySQL; `/users` and `/analytics` from PostgreSQL | assigned per run (see dashboard) |
| `frontend` | FastAPI + Jinja2 (Python) | Page showing contacts, users and analytics | assigned per run (see dashboard) |
| `mysql` | MySQL 9 container | Contacts data | assigned per run |
| `postgres` | PostgreSQL 18 container | Users, analytics events, Superset metadata | assigned per run |
| `superset` | Apache Superset (custom image) | BI dashboards | http://localhost:8088 |
| `jupyter` | JupyterLab (custom image) | Notebooks | http://localhost:8889 |
| Aspire dashboard | | Resource status, logs, endpoints | http://localhost:15170 |

```
frontend ──► api ──┬──► MySQL      (contacts)
                   └──► PostgreSQL (users, analytics_events)
Superset ──► PostgreSQL (metadata) + both databases for charts
Jupyter  ──► both databases
```

## Quick start (install and start)

macOS with [Homebrew](https://brew.sh) assumed. Steps 1-2 are one-time setup.

**1. Install the prerequisites**

```bash
brew install --cask dotnet-sdk docker     # .NET 10 SDK and Docker Desktop
brew install uv python                    # Python tooling
dotnet tool install -g Aspire.Cli --version 13.6.0   # optional: the `aspire` command
echo 'export PATH="$PATH:$HOME/.dotnet/tools"' >> ~/.zshrc && source ~/.zshrc
```

Open **Docker Desktop** once, accept its prompts and wait until it says it is running. It must be version 25 or newer
(`docker version --format '{{.Client.Version}}'`). Optionally trust the HTTPS dev certificate:
`dotnet dev-certs https --trust`.

**2. Get the code and configure it**

```bash
git clone https://github.com/sarathchandrac/contacts-aspire.git
cd contacts-aspire
cp AppHost/appsettings.Development.example.json AppHost/appsettings.Development.json
```

Edit `AppHost/appsettings.Development.json`:
- replace every `CHANGE_ME` with your own password / token (Superset's secret key should be a long random string);
- `FsRoot` is where database files, logs and notebooks are stored. The default `../fs` is a folder next to the project.
  Set an absolute path to keep the data elsewhere.

Choose the passwords **before the first start**: the databases keep them on disk, so changing a password later means wiping that database's data folder.

**3. Start all services**

```bash
aspire run                                   # with the Aspire CLI
# or, without the CLI:
cd AppHost && dotnet run --launch-profile http
```

The first start takes a few minutes (it pulls images, builds the Superset and Jupyter images and installs Python packages).
Watch the console for the dashboard `Login URL`, open it, and wait until every resource shows **Running**.

**4. Open the services**

| What | Where |
|---|---|
| Aspire dashboard | http://localhost:15170 (use the `Login URL` from the console) |
| Frontend and API | the `frontend` and `api` links in the dashboard's URLs column |
| Superset | http://localhost:8088 (user `admin`, password from your settings file) |
| Jupyter | http://localhost:8889/?token=*your-jupyter-token* |

**5. Create the starter Superset dashboard (optional)**

With Superset running, register the data and build the dashboard:

```bash
python3 superset/create_dashboard.py
```

Open http://localhost:8088/superset/dashboard/1/. The Jupyter notebook `analytics_overview.ipynb` (in `jupyter/`) shows the same
analytics; copy it to `<FsRoot>/jupyter/work/` to open it in JupyterLab.

**6. Stop**

Press **Ctrl+C** in the terminal running Aspire (or `aspire stop`). The MySQL and PostgreSQL containers are persistent;
see [Stop, restart and clean up](#stop-restart-and-clean-up) to stop them as well.

## Prerequisites

| Tool | Version | Check |
|---|---|---|
| .NET SDK | 10 | `dotnet --version` |
| Docker Desktop | **25 or newer** (Aspire rejects older CLIs) | `docker version --format '{{.Client.Version}}'` |
| uv | any recent | `uv --version` |
| Python | 3.11+ | `python3 --version` |
| Aspire CLI (optional) | 13.6.0 | `aspire --version` |

Install the optional Aspire CLI and put .NET tools on your PATH:

```bash
dotnet tool install -g Aspire.Cli --version 13.6.0
echo 'export PATH="$PATH:$HOME/.dotnet/tools"' >> ~/.zshrc && source ~/.zshrc
```

Docker Desktop must be **running** before you start Aspire (`docker info` should succeed). Give it enough memory:
Superset, Jupyter, MySQL and PostgreSQL together need roughly 4 GB or more (Docker Desktop → Settings → Resources).

## Project layout

```
AppHost/                    Aspire app host (AppHost.cs defines every service)
  appsettings.Development.json   dev passwords / tokens (local only, keep out of git)
api/                        FastAPI backend (main.py, db.py)
frontend/                   FastAPI + Jinja2 frontend (main.py, templates/)
superset/                   Superset image, config, bootstrap, create_dashboard.py
jupyter/                    Jupyter image + copy of the analytics notebook
```

Persistent data and logs are bind-mounted to the host under `FsRoot` from `AppHost/appsettings.Development.json`
(default `fs/` next to the project; the folders are created automatically and git-ignored):

```
fs/mysql/data      fs/mysql/logs       (error.log, general.log, slow.log)
fs/postgres/data   fs/postgres/logs    (postgres.log)
fs/jupyter/work                        (notebooks)
```

## Run everything

Option A: Aspire CLI

```bash
cd contacts-aspire
aspire run
```

Option B: plain .NET (no CLI needed)

```bash
cd contacts-aspire/AppHost
dotnet run --launch-profile http
```

Then:

1. Open the dashboard at **http://localhost:15170**. The console prints a one-time `Login URL` with a token; open that link.
2. Wait for every resource to show **Running**. The first start is slow (it pulls images, builds the Superset and Jupyter images, and installs Python packages). Later starts are fast.
3. Open the services from the **URLs** column of the dashboard.

Startup order is handled by Aspire: databases → `api` (waits for MySQL and PostgreSQL, creates tables and seeds data on first start) → `frontend`.

### HTTP vs HTTPS

`aspire run` serves the dashboard over HTTPS and needs a trusted dev certificate. Trust it once (asks for your password):

```bash
dotnet dev-certs https --trust
```

The `http` launch profile in `AppHost/Properties/launchSettings.json` avoids this by using plain HTTP for the dashboard.

## Credentials

All dev credentials are in `AppHost/appsettings.Development.json`. That file is git-ignored; on a fresh clone create it with
`cp AppHost/appsettings.Development.example.json AppHost/appsettings.Development.json` and replace the `CHANGE_ME` values
(or move the values to `dotnet user-secrets`). They are fixed on purpose: the databases persist on disk, so a new random password on each run would lock you out.

| Service | Login |
|---|---|
| MySQL | user `root`, password `mysql-password` |
| PostgreSQL | user `postgres`, password `postgres-password` |
| Superset | user `admin`, password `superset-admin-password` |
| Jupyter | token `jupyter-token` (open `http://localhost:8889/?token=<token>`) |

## The services

### API (`api`)

| Endpoint | Source | Returns |
|---|---|---|
| `GET /contacts` | MySQL | 20 contacts (name, phone, email) |
| `GET /users` | PostgreSQL | 10 users |
| `GET /analytics` | PostgreSQL | totals, by event type, by page, top users (200 seeded events) |
| `GET /health`, `GET /docs` | | health check, interactive docs |

Tables are created and seeded on first start. Delete the contents of `fs/mysql/data` and `fs/postgres/data` to reseed from scratch.

### Frontend (`frontend`)

Open its URL from the dashboard. It shows three sections: Contacts (MySQL), Users (PostgreSQL) and Analytics (PostgreSQL).
Aspire passes the API address to it through service discovery.

### MySQL and PostgreSQL

Connect with any client using the host port shown in the dashboard (it changes between runs unless you set a fixed port):

```bash
mysql -h 127.0.0.1 -P <mysql-port> -u root -p contacts
psql  -h localhost -p <postgres-port> -U postgres contacts
```

Inside containers (Superset, Jupyter) use `mysql.dev.internal:3306` and `postgres.dev.internal:5432`.

### Superset

- Open **http://localhost:8088** and log in as `admin`.
- Superset's own metadata lives in the `superset` database on the PostgreSQL container.
- Both databases are registered under Settings → Database Connections:
  `Contacts (MySQL)` and `Contacts & Analytics (PostgreSQL)`. To (re)register them manually:
  - `mysql+pymysql://root:<password>@mysql.dev.internal:3306/contacts`
  - `postgresql+psycopg2://postgres:<password>@postgres.dev.internal:5432/contacts`
- Create the starter **Analytics Overview** dashboard (five charts over `analytics_events` joined to `users`).
  It is safe to re-run; it updates objects by name:

  ```bash
  python3 superset/create_dashboard.py
  ```

  The dashboard is then at http://localhost:8088/superset/dashboard/1/.

### Jupyter

- Open **http://localhost:8889/?token=\<jupyter-token\>**.
- Notebooks are saved in `fs/jupyter/work`. `analytics_overview.ipynb` reproduces the dashboard with pandas and matplotlib.
- The container has `MYSQL_*` and `POSTGRES_*` environment variables, so notebooks connect via `os.environ`:

  ```python
  import os, pandas as pd
  from sqlalchemy import create_engine
  pg = "postgresql+psycopg://{u}:{p}@{h}:{port}/{db}".format(
      u=os.environ["POSTGRES_USER"], p=os.environ["POSTGRES_PASSWORD"],
      h=os.environ["POSTGRES_HOST"], port=os.environ["POSTGRES_PORT"], db=os.environ["POSTGRES_DATABASE"])
  pd.read_sql("select * from users", create_engine(pg))
  ```

- Jupyter is published on host port **8889** because 8888 is commonly used by a locally installed Jupyter.

## Check that everything is running

```bash
docker ps --format '{{.Names}}  {{.Status}}'      # mysql-*, postgres-*, superset-*, jupyter-* should be Up
curl -s -o /dev/null -w '%{http_code}\n' http://localhost:8088/health    # Superset: 200
curl -s -o /dev/null -w '%{http_code}\n' http://localhost:8889/api       # Jupyter: 200
```

Use the dashboard's URLs column for the API, frontend and database ports (they change on every run), then check the API with
`curl -sk https://localhost:<api-port>/contacts` (use `-k` because the dev certificate is self-signed).
All checks pass when `/contacts`, `/users` and `/analytics` return 200.

## Stop, restart and clean up

Stop everything: press **Ctrl+C** in the terminal running Aspire, or from any terminal:

```bash
aspire stop                                  # if the Aspire CLI is installed
pkill -INT -f contacts-aspire/AppHost        # otherwise
```

The MySQL and PostgreSQL containers are **persistent** and keep running after Aspire stops. Stop them with:

```bash
docker ps --format '{{.Names}}' | grep -E '^(mysql|postgres)-'   # find the names
docker stop <mysql-container> <postgres-container>
```

Data survives restarts because it lives in `fs/`. If the containers were killed (for example by a Docker crash), MySQL and
PostgreSQL run crash recovery on the next start, so that first start can take a little longer. To wipe a database, stop its
container and delete the folder contents (for example `fs/mysql/data/*`).

## Troubleshooting

| Symptom | Cause and fix |
|---|---|
| `No trusted development certificate was found` | Run `dotnet dev-certs https --trust`, or use the `http` launch profile. |
| `Container runtime 'docker' ... unhealthy` | Docker Desktop isn't running, or its CLI is older than 25. Start/upgrade Docker, then restart Aspire. Check with `~/.nuget/packages/aspire.hosting.orchestration.osx-arm64/13.6.0/tools/dcp info`. |
| `dotnet run` fails with `Parameter ... not found` | `AppHost/appsettings.Development.json` is missing or incomplete; create it from the `.example.json` file (Quick start, step 2). |
| `aspire: command not found` | Add `$HOME/.dotnet/tools` to PATH (see Prerequisites), or use `dotnet run --launch-profile http`. |
| `api` fails at `api-installer` | `pip install .` failed. Open the `api-installer` console log in the dashboard; both `pyproject.toml` files must list their modules under `[tool.setuptools] py-modules`. |
| Frontend: "Could not load /contacts" | The API isn't ready or its database is down. Check the `api` logs in the dashboard. |
| Superset MySQL query: `No module named MySQLdb` | `superset/superset_config.py` must call `pymysql.install_as_MySQLdb()`; rebuild the image by restarting Aspire. |
| Jupyter doesn't start, port in use | Something else holds 8889. Change the host port in `AppHost.cs` (`WithHttpEndpoint(port: 8889, ...)`). |
| Old `superset-*` / `jupyter-*` containers show as `Exited` | Leftovers from an earlier run or a Docker crash. They are harmless; remove them with `docker container prune` (it only removes stopped containers). |
| `docker stop` of several containers fails with `404 page not found` | Stop them one at a time (`docker stop <name>` for each). |
| Docker API returns 500 / `docker ps` hangs | Docker Desktop engine is overloaded or hung. Restart Docker Desktop (force-quit if needed), raise its memory limit, then restart Aspire. |
| Aspire warns `Failed to persist public port` | Harmless. Run `dotnet user-secrets init` in `AppHost/` to remove the warning. |
| Database container exits at startup | Check its logs in the dashboard. Bind-mounted folders under `fs/` must be writable. |

## Rebuilding after changes

- **Python code** (`api/`, `frontend/`): uvicorn runs with `--reload`, so edits apply automatically.
- **Superset / Jupyter images** (`superset/`, `jupyter/`): restart Aspire; it rebuilds the changed image layers.
- **AppHost.cs**: restart Aspire.
