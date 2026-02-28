# How to Run Alembic Migrations

To apply the latest database migrations, use the following command from the `sound-first-service` directory:

```
alembic upgrade head
```

To create a new migration after changing models, use:

```
alembic revision --autogenerate -m "Your migration message here"
```

To downgrade (undo) the last migration, use:

```
alembic downgrade -1
```

For more, see the [Alembic documentation](https://alembic.sqlalchemy.org/en/latest/).
