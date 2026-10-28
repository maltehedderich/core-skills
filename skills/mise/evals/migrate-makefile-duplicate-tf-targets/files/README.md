# acme-api

## Development

```sh
cp .env.example .env
make install
make run
```

Run the tests with `make test` and format with `make fmt` before pushing.

## Infrastructure

```sh
make tf-plan ENV=staging
make tf-apply ENV=staging
```

Production plans: `make tf-plan-prod`.
