## Deployment: Secrets

Sensitive values (e.g. the database password) are provided to containers as
Docker Compose **file-based secrets**. Each secret is a plain file on the host
that Compose mounts read-only into the container at `/run/secrets/<name>`.

```yaml
secrets:
  db_password:
    file: ./secrets/db_password
    ...
```

### Why a shared group

For file-based secrets, Compose ignores the `uid`, `gid`, and `mode` options on
the service-level secret reference (those only work for Swarm or env-sourced
secrets). The mounted file keeps the **numeric owner and mode of the source
file** on the host. Because our services run as non-root users with *different*
UIDs (Postgres `999`, RustFS `10001`, the init container `1000`), a
`root`-owned `0600` file would be unreadable by them.

Rather than making the file world-readable (`0644`) or maintaining one copy per
UID, all services share a common group, `secrets` (**GID 5000**), and the secret
is group-readable.

### Host setup

Create the secret file and set the correct access rights:

```bash
mkdir -p ./secrets
...
chown -R root:5000 . 
chmod 640 ./*  # owner rw, group r, others none
```

> The **GID `5000` is the only value that must match** between the host file and
> the containers. The group *name* is arbitrary. Keep `./secrets/` out of version
> control.