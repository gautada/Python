# python
Public python code that is used for standard scripts in python environment.

## Postgresql

This script is provided to test a postgresql server. The package
`psscopg2-binary` is required. An `.ini` also needs to be provided

```ini
[postgresql]
host = localhost
port = 5432
database = postgres
user = postgres
password = mypassword
sslmode = verify-full
sslrootcert=/etc/ssl/cert.pem
```

Test Query - Goal is that it should work on any and all databases

```sql
SELECT table_schema, table_name
FROM information_schema.tables
WHERE table_type = 'BASE TABLE';
```

4️⃣ Understanding SSL Modes:
The sslmode parameter defines how SSL is used:

disable – No SSL (unencrypted connection).
allow – SSL is attempted, but falls back to unencrypted if unavailable.
prefer – SSL is used if available (default in some cases).
require – SSL is always used (no verification).
verify-ca – SSL with certificate validation (checks CA).
verify-full – Strictest mode (verifies CA & hostname).
Use verify-full for the most secure setup.
