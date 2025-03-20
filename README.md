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
```

Test Query - Goal is that it should work on any and all databases

```sql
SELECT table_schema, table_name
FROM information_schema.tables
WHERE table_type = 'BASE TABLE';
```
