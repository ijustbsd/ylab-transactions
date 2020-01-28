#!/bin/sh
set -e

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    CREATE TABLE Currencies (
        id VARCHAR(3) PRIMARY KEY,
        rate NUMERIC(20,8) NOT NULL,
        multiplier Integer NOT NULL
    );

    CREATE TABLE Users (
        email VARCHAR(127) PRIMARY KEY,
        password BYTEA NOT NULL,
        balance NUMERIC(20,8) NOT NULL CHECK (balance >= 0),
        currency VARCHAR(3) NOT NULL,
        FOREIGN KEY (currency) REFERENCES Currencies (id) ON DELETE RESTRICT
    );

    CREATE TABLE Transactions (
        id BIGSERIAL PRIMARY KEY,
        sender VARCHAR(127) NOT NULL,
        recipient VARCHAR(127) NOT NULL,
        date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        amount NUMERIC(20,8) NOT NULL CHECK (amount >= 0),
        FOREIGN KEY (sender) REFERENCES Users (email) ON DELETE RESTRICT
    );

    INSERT INTO Currencies VALUES ('USD', 1.0, 1);
    INSERT INTO Currencies VALUES ('EUR', 1.0, 1);
    INSERT INTO Currencies VALUES ('GBP', 1.0, 1);
    INSERT INTO Currencies VALUES ('RUB', 1.0, 1);
    INSERT INTO Currencies VALUES ('BTC', 1.0, 1);
EOSQL
