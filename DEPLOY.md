# PaperFlow controlled alpha deployment

The repository is configured for a single-instance Render deployment with persistent
project storage. It is intentionally a controlled alpha, protected by one shared access
code, rather than an open multi-tenant service.

## Required secrets

- `PAPERFLOW_ACCESS_TOKEN`: long random access code used as the Basic-auth password.
- At least one of `OPENAI_API_KEY` or `DEEPSEEK_API_KEY`. The current default model
  routes and fallback chain use these two providers.

The default model routes in `render.yaml` use OpenAI for reasoning and DeepSeek for
writing. Change the routes if the corresponding keys are not configured.

## Render

1. Push this branch to a private GitHub repository.
2. In Render, create a Blueprint from the repository. Render reads `render.yaml`.
3. Enter the access token and model secrets when prompted.
4. Confirm that the persistent disk is mounted at `/var/data`.
5. After the health check passes, open the service URL and enter any username plus the
   configured access token as the password.

The server deliberately runs one worker and one model job at a time. Project files,
workflow revisions, interview answers, graph audits, and generated artifacts are stored
under `/var/data/projects` and survive service restarts. A job interrupted by a restart
is marked `interrupted` and can be retried from the last stage.

## Release gate

Run before deployment:

```bash
PYTHONPATH=engine/src python -m pytest -q engine/tests
python -m compileall -q engine/src
git diff --check
```

The alpha accepts up to 20 MB per uploaded file, 100 MB per project, and 800 MB across
the service disk. File extraction
uses stricter parser limits and rejects path traversal, hidden paths, and symlinks. A
logic graph must pass the deterministic audit and its exact revision must be confirmed
before manuscript generation starts.

## Current boundary

This is not yet an open SaaS deployment: there are no individual user accounts, billing,
or horizontally distributed job workers. Do not remove the access token or increase the
worker count until per-user ownership and a durable shared queue are implemented.
