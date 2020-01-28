#!/bin/sh
set -e

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    CREATE TABLE Users (
        email VARCHAR(127) PRIMARY KEY,
        password BYTEA NOT NULL,
        balance NUMERIC(20,8) NOT NULL CHECK (balance >= 0),
        currency VARCHAR(3) NOT NULL
    );

    CREATE TABLE Transactions (
        id BIGSERIAL PRIMARY KEY,
        sender VARCHAR(127) NOT NULL,
        recipient VARCHAR(127) NOT NULL,
        date TIMESTAMP NOT NULL,
        amount NUMERIC(20,8) NOT NULL CHECK (amount >= 0),
        FOREIGN KEY (sender) REFERENCES Users (email) ON DELETE RESTRICT
    );
EOSQL
