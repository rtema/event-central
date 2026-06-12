#!/usr/bin/env python3
"""
Initialize the primary and secondary RustFS instances for local development.

RustFS is a reliable S3 *data* layer, but as of mid-2026 its IAM admin API
(headless creation of users / access keys and attaching policies) is not
dependable: `mc admin` returns "Unknown operation", the AWS IAM API returns
500s, and the canned-policy admin endpoint is broken on recent builds. What is
confirmed to work is that an access key created in the RustFS console functions
correctly over the S3 API.

So this initializer uses a strategy suited to what RustFS can do headlessly:

  * create every bucket named in the comma-separated BUCKETS env var on each
    instance (S3 MakeBucket -- fully reliable), and
  * VERIFY the restricted application access key, using the credentials supplied
    as Docker secrets: it writes an object (expect OK), reads it back (expect
    OK), and attempts to delete it (expect DENIED), reporting the result.

The access key itself, with the read+write/no-delete policy, is created once in
the RustFS console -- this script prints the exact policy JSON to paste. After
that, re-running this container confirms the key behaves correctly.

Only mc's S3 operations are used (no admin calls). The restricted key is
configured through an MC_HOST_* env var so mc skips the ListAllMyBuckets
validation that the restricted policy would (correctly) deny.
"""

import json
import os
import subprocess
import sys
import tempfile
import time
from typing import Any
from urllib.parse import quote, urlsplit

# Type aliases for readability.
Env = dict[str, str]            # process environment passed to mc
CheckResult = tuple[str, str]   # (status, human-readable detail)
Policy = dict[str, Any]         # an S3/IAM policy document


PROBE_OBJECT: str = ".rwnd-init-probe"


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------

def log(message: str) -> None:
    print(f"[init] {message}", flush=True)


def banner(message: str) -> None:
    line = "=" * 70
    print(f"\n{line}\n{message}\n{line}", flush=True)


def read_secret(name: str) -> str:
    path = os.environ.get(f"{name.upper()}_FILE", f"/run/secrets/{name}")
    try:
        with open(path, "r", encoding="utf-8") as handle:
            value = handle.read().strip()
    except FileNotFoundError:
        log(f"ERROR: secret '{name}' not found at {path}")
        sys.exit(1)
    if not value:
        log(f"ERROR: secret '{name}' at {path} is empty")
        sys.exit(1)
    return value


def run_mc(args: list[str], env: Env | None = None) -> tuple[int, str]:
    """Run an mc command, returning (returncode, combined_output)."""
    result = subprocess.run(
        ["mc", "--no-color", *args],
        capture_output=True,
        text=True,
        env=env,
    )
    return result.returncode, (result.stdout + result.stderr).strip()


def mc_host_env(endpoint: str, access_key: str, secret_key: str) -> str:
    """Build an MC_HOST_<alias>-style environment value for a credential,
    avoiding mc's alias-set validation call (which lists all buckets)."""
    parts = urlsplit(endpoint)
    creds = f"{quote(access_key, safe='')}:{quote(secret_key, safe='')}"
    return f"{parts.scheme}://{creds}@{parts.netloc}"


# --------------------------------------------------------------------------
# policy
# --------------------------------------------------------------------------

def build_policy(buckets: list[str]) -> Policy:
    """Read + write on the given buckets, with deletes explicitly denied."""
    bucket_arns = [f"arn:aws:s3:::{b}" for b in buckets]
    object_arns = [f"arn:aws:s3:::{b}/*" for b in buckets]
    return {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "ListAndLocate",
                "Effect": "Allow",
                "Action": ["s3:ListBucket", "s3:GetBucketLocation"],
                "Resource": bucket_arns,
            },
            {
                "Sid": "ReadWriteObjects",
                "Effect": "Allow",
                "Action": ["s3:GetObject", "s3:PutObject"],
                "Resource": object_arns,
            },
            {
                "Sid": "DenyDeletes",
                "Effect": "Deny",
                "Action": ["s3:DeleteObject", "s3:DeleteObjectVersion"],
                "Resource": object_arns,
            },
        ],
    }


# --------------------------------------------------------------------------
# steps
# --------------------------------------------------------------------------

def wait_and_create_buckets(instance: str, endpoint: str, root_key: str,
                            root_secret: str, buckets: list[str],
                            retries: int = 30, delay: int = 2) -> Env:
    """Wait for the instance, then create all buckets (idempotent)."""
    admin_env = {**os.environ, f"MC_HOST_{instance}": mc_host_env(endpoint, root_key, root_secret)}

    for attempt in range(1, retries + 1):
        rc, out = run_mc(["ls", instance], env=admin_env)
        if rc == 0:
            break
        log(f"[{instance}] {endpoint} not ready (attempt {attempt}/{retries})")
        time.sleep(delay)
    else:
        log(f"ERROR: could not reach {endpoint} after {retries} attempts")
        sys.exit(1)

    for bucket in buckets:
        log(f"[{instance}] creating bucket '{bucket}'")
        rc, out = run_mc(["mb", "--ignore-existing", f"{instance}/{bucket}"], env=admin_env)
        if rc != 0:
            log(f"ERROR creating bucket '{bucket}': {out}")
            sys.exit(rc)
    return admin_env


def verify_restricted_key(instance: str, endpoint: str, admin_env: Env,
                          user_key: str, user_secret: str,
                          bucket: str) -> CheckResult:
    """Write/read/delete probe with the restricted key. Returns a status string."""
    user_env = {**os.environ, f"MC_HOST_{instance}-user": mc_host_env(endpoint, user_key, user_secret)}
    target = f"{instance}-user/{bucket}/{PROBE_OBJECT}"

    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as fh:
        fh.write("read-write-no-delete probe\n")
        probe_path = fh.name

    # WRITE (expect success)
    rc, out = run_mc(["cp", "--quiet", probe_path, target], env=user_env)
    if rc != 0:
        low = out.lower()
        # mc prints human-readable messages, not the raw S3 error codes, so
        # match on the wording as well as the codes.
        if any(s in low for s in (
            "does not exist in our records",   # mc wording for InvalidAccessKeyId
            "invalidaccesskeyid",
            "the access key id you provided",
        )):
            return ("PENDING", "access key does not exist yet -- create it in the console (policy below)")
        if "signaturedoesnotmatch" in low or "signature we calculated" in low:
            return ("PENDING", "secret mismatch -- the key's secret must equal storage_<instance>_user_secret")
        if "accessdenied" in low or "access denied" in low:
            return ("PENDING", "write denied -- the access key's policy is missing s3:PutObject")
        return ("ERROR", f"unexpected write failure: {out}")

    # READ (expect success)
    out_path = probe_path + ".out"
    rc, out = run_mc(["cp", "--quiet", target, out_path], env=user_env)
    read_ok = rc == 0

    # DELETE (expect denial)
    rc, out = run_mc(["rm", target], env=user_env)
    delete_blocked = (rc != 0) and ("AccessDenied" in out or "Access Denied" in out or "denied" in out.lower())

    # Clean up the probe with root rights regardless of the outcome.
    run_mc(["rm", "--force", f"{instance}/{bucket}/{PROBE_OBJECT}"], env=admin_env)

    if read_ok and delete_blocked:
        return ("PASS", "write OK, read OK, delete correctly denied")
    if read_ok and not delete_blocked:
        return ("FAIL", "delete was NOT denied -- the no-delete policy is not in effect")
    return ("FAIL", "write OK but read failed -- check the read part of the policy")


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------

def main() -> None:
    # Root credentials now come from Docker secrets, same as the user creds.
    root_key = read_secret("storage_root_key")
    root_secret = read_secret("storage_root_secret")

    buckets = [b.strip() for b in os.environ.get("BUCKETS", "").split(",") if b.strip()]
    if not buckets:
        log("ERROR: no buckets specified (set BUCKETS=bucket1,bucket2,...)")
        sys.exit(1)
    log(f"buckets to provision: {', '.join(buckets)}")

    instances: list[dict[str, str]] = [
        {
            "name": "primary",
            "endpoint": os.environ["PRIMARY_ENDPOINT"],
            "console": os.environ["PRIMARY_CONSOLE"],
            "user_key": read_secret("storage_primary_user_key"),
            "user_secret": read_secret("storage_primary_user_secret"),
        },
        {
            "name": "secondary",
            "endpoint": os.environ["SECONDARY_ENDPOINT"],
            "console": os.environ["SECONDARY_CONSOLE"],
            "user_key": read_secret("storage_secondary_user_key"),
            "user_secret": read_secret("storage_secondary_user_secret"),
        },
    ]

    results: dict[str, CheckResult] = {}
    for inst in instances:
        admin_env = wait_and_create_buckets(
            inst["name"], inst["endpoint"], root_key, root_secret, buckets
        )
        status, detail = verify_restricted_key(
            inst["name"], inst["endpoint"], admin_env,
            inst["user_key"], inst["user_secret"], buckets[0],
        )
        results[inst["name"]] = (status, detail)
        log(f"[{inst['name']}] access-key check: {status} ({detail})")

    # If any instance still needs its access key created, print the policy.
    if any(status in ("PENDING", "FAIL") for status, _ in results.values()):
        policy_json = json.dumps(build_policy(buckets), indent=2)

        consoles = "".join([f"  {inst["name"]} -> {inst["console"]} \n" for inst in instances])
        banner(
            "ACTION REQUIRED: create the application access key in the console\n\n"
            "RustFS cannot reliably create a restricted access key headlessly,\n"
            "so create one per instance in the web console:\n"
            "  (Access Keys -> Add)\n"
            f"{consoles}"
            "\n"
            "Use the key/secret from secrets/storage_<instance>_user_key|secret\n"
            "and paste this policy as the access key's custom policy:\n\n"
            f"{policy_json}\n\n"
            "Then re-run:  docker compose run --rm rustfs-init"
        )

    banner("SUMMARY\n" + "\n".join(
        f"  {name:<10} buckets: OK   access-key: {status} ({detail})"
        for name, (status, detail) in results.items()
    ))

    log("bucket provisioning complete")


if __name__ == "__main__":
    main()