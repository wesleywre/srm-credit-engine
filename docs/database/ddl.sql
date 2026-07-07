-- =============================================================================
-- SRM Credit Engine — DDL completo do schema (PostgreSQL 16)
--
-- Gerado a partir das migrations Alembic (fonte da verdade):
--   cd backend && uv run alembic upgrade base:head --sql > ../docs/database/ddl.sql
-- Não edite manualmente — altere os models/migrations e regenere.
-- =============================================================================

BEGIN;

CREATE TABLE alembic_version (
    version_num VARCHAR(32) NOT NULL,
    CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
);

-- Running upgrade  -> cf5cd043f352

CREATE TABLE assignors (
    id UUID NOT NULL,
    name VARCHAR(120) NOT NULL,
    document VARCHAR(14) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    CONSTRAINT pk_assignors PRIMARY KEY (id),
    CONSTRAINT ck_assignors_document_length CHECK (char_length(document) = 14),
    CONSTRAINT uq_assignors_document UNIQUE (document)
);

COMMENT ON COLUMN assignors.document IS 'CNPJ (digits only)';

CREATE TABLE currencies (
    code VARCHAR(3) NOT NULL,
    name VARCHAR(50) NOT NULL,
    decimal_places SMALLINT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    CONSTRAINT pk_currencies PRIMARY KEY (code)
);

COMMENT ON COLUMN currencies.code IS 'ISO 4217 code';

COMMENT ON COLUMN currencies.decimal_places IS 'Rounding precision for monetary amounts';

CREATE TABLE receivable_types (
    id SERIAL NOT NULL,
    code VARCHAR(30) NOT NULL,
    name VARCHAR(80) NOT NULL,
    monthly_spread NUMERIC(10, 6) NOT NULL,
    active BOOLEAN NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    CONSTRAINT pk_receivable_types PRIMARY KEY (id),
    CONSTRAINT ck_receivable_types_monthly_spread_non_negative CHECK (monthly_spread >= 0),
    CONSTRAINT uq_receivable_types_code UNIQUE (code)
);

COMMENT ON COLUMN receivable_types.code IS 'DUPLICATA, CHEQUE, ...';

COMMENT ON COLUMN receivable_types.monthly_spread IS 'Risk spread per month as a decimal fraction (0.015 = 1.5% p.m.)';

CREATE TABLE base_rates (
    id UUID NOT NULL,
    currency_code VARCHAR(3) NOT NULL,
    monthly_rate NUMERIC(10, 6) NOT NULL,
    effective_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    CONSTRAINT pk_base_rates PRIMARY KEY (id),
    CONSTRAINT ck_base_rates_monthly_rate_non_negative CHECK (monthly_rate >= 0),
    CONSTRAINT fk_base_rates_currency_code_currencies FOREIGN KEY(currency_code) REFERENCES currencies (code),
    CONSTRAINT uq_base_rates_currency_code UNIQUE (currency_code, effective_at)
);

COMMENT ON COLUMN base_rates.monthly_rate IS 'Monthly base rate as a decimal fraction (0.01 = 1% p.m.)';

COMMENT ON COLUMN base_rates.effective_at IS 'Moment from which this rate is valid';

CREATE INDEX ix_base_rates_currency_effective ON base_rates (currency_code, effective_at);

CREATE TABLE batches (
    id UUID NOT NULL,
    assignor_id UUID NOT NULL,
    payment_currency_code VARCHAR(3) NOT NULL,
    status VARCHAR(20) NOT NULL,
    version INTEGER NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    CONSTRAINT pk_batches PRIMARY KEY (id),
    CONSTRAINT ck_batches_status_valid CHECK (status IN ('PENDING', 'SETTLED')),
    CONSTRAINT ck_batches_version_positive CHECK (version >= 1),
    CONSTRAINT fk_batches_assignor_id_assignors FOREIGN KEY(assignor_id) REFERENCES assignors (id),
    CONSTRAINT fk_batches_payment_currency_code_currencies FOREIGN KEY(payment_currency_code) REFERENCES currencies (code)
);

COMMENT ON COLUMN batches.version IS 'Optimistic locking token';

CREATE INDEX ix_batches_assignor_id ON batches (assignor_id);

CREATE TABLE exchange_rates (
    id UUID NOT NULL,
    base_currency_code VARCHAR(3) NOT NULL,
    quote_currency_code VARCHAR(3) NOT NULL,
    rate NUMERIC(20, 10) NOT NULL,
    source VARCHAR(30) NOT NULL,
    effective_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    CONSTRAINT pk_exchange_rates PRIMARY KEY (id),
    CONSTRAINT ck_exchange_rates_distinct_currencies CHECK (base_currency_code <> quote_currency_code),
    CONSTRAINT ck_exchange_rates_rate_positive CHECK (rate > 0),
    CONSTRAINT fk_exchange_rates_base_currency_code_currencies FOREIGN KEY(base_currency_code) REFERENCES currencies (code),
    CONSTRAINT fk_exchange_rates_quote_currency_code_currencies FOREIGN KEY(quote_currency_code) REFERENCES currencies (code),
    CONSTRAINT uq_exchange_rates_base_currency_code UNIQUE (base_currency_code, quote_currency_code, effective_at)
);

COMMENT ON COLUMN exchange_rates.rate IS 'Units of quote currency per 1 unit of base currency';

COMMENT ON COLUMN exchange_rates.source IS 'MANUAL or MOCK_PROVIDER';

COMMENT ON COLUMN exchange_rates.effective_at IS 'Moment from which this rate is valid';

CREATE INDEX ix_exchange_rates_pair_effective ON exchange_rates (base_currency_code, quote_currency_code, effective_at);

CREATE TABLE receivables (
    id UUID NOT NULL,
    batch_id UUID NOT NULL,
    receivable_type_id INTEGER NOT NULL,
    face_value NUMERIC(18, 2) NOT NULL,
    currency_code VARCHAR(3) NOT NULL,
    due_date DATE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    CONSTRAINT pk_receivables PRIMARY KEY (id),
    CONSTRAINT ck_receivables_face_value_positive CHECK (face_value > 0),
    CONSTRAINT fk_receivables_batch_id_batches FOREIGN KEY(batch_id) REFERENCES batches (id),
    CONSTRAINT fk_receivables_currency_code_currencies FOREIGN KEY(currency_code) REFERENCES currencies (code),
    CONSTRAINT fk_receivables_receivable_type_id_receivable_types FOREIGN KEY(receivable_type_id) REFERENCES receivable_types (id)
);

COMMENT ON COLUMN receivables.face_value IS 'Face value in the receivable currency';

CREATE INDEX ix_receivables_batch_id ON receivables (batch_id);

CREATE TABLE settlements (
    id UUID NOT NULL,
    batch_id UUID NOT NULL,
    payment_currency_code VARCHAR(3) NOT NULL,
    fx_rate NUMERIC(20, 10),
    fx_rate_id UUID,
    total_face_value NUMERIC(18, 2) NOT NULL,
    total_present_value NUMERIC(18, 2) NOT NULL,
    total_discount NUMERIC(18, 2) NOT NULL,
    settled_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    CONSTRAINT pk_settlements PRIMARY KEY (id),
    CONSTRAINT ck_settlements_total_discount_non_negative CHECK (total_discount >= 0),
    CONSTRAINT ck_settlements_total_present_value_non_negative CHECK (total_present_value >= 0),
    CONSTRAINT fk_settlements_batch_id_batches FOREIGN KEY(batch_id) REFERENCES batches (id),
    CONSTRAINT fk_settlements_fx_rate_id_exchange_rates FOREIGN KEY(fx_rate_id) REFERENCES exchange_rates (id),
    CONSTRAINT fk_settlements_payment_currency_code_currencies FOREIGN KEY(payment_currency_code) REFERENCES currencies (code),
    CONSTRAINT uq_settlements_batch_id UNIQUE (batch_id)
);

COMMENT ON COLUMN settlements.fx_rate IS 'FX rate applied for cross-currency batches (null when same currency)';

COMMENT ON COLUMN settlements.fx_rate_id IS 'Provenance of the applied FX rate';

COMMENT ON COLUMN settlements.total_face_value IS 'Sum of face values, in payment currency';

COMMENT ON COLUMN settlements.total_present_value IS 'Sum of present values, in payment currency';

COMMENT ON COLUMN settlements.total_discount IS 'Total desagio (face - present), in payment currency';

CREATE TABLE settlement_items (
    id UUID NOT NULL,
    settlement_id UUID NOT NULL,
    receivable_id UUID NOT NULL,
    face_value NUMERIC(18, 2) NOT NULL,
    currency_code VARCHAR(3) NOT NULL,
    base_rate_monthly NUMERIC(10, 6) NOT NULL,
    spread_monthly NUMERIC(10, 6) NOT NULL,
    term_months NUMERIC(10, 4) NOT NULL,
    present_value NUMERIC(18, 2) NOT NULL,
    discount_amount NUMERIC(18, 2) NOT NULL,
    fx_rate NUMERIC(20, 10),
    present_value_payment NUMERIC(18, 2) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    CONSTRAINT pk_settlement_items PRIMARY KEY (id),
    CONSTRAINT fk_settlement_items_currency_code_currencies FOREIGN KEY(currency_code) REFERENCES currencies (code),
    CONSTRAINT fk_settlement_items_receivable_id_receivables FOREIGN KEY(receivable_id) REFERENCES receivables (id),
    CONSTRAINT fk_settlement_items_settlement_id_settlements FOREIGN KEY(settlement_id) REFERENCES settlements (id),
    CONSTRAINT uq_settlement_items_receivable_id UNIQUE (receivable_id)
);

COMMENT ON COLUMN settlement_items.face_value IS 'Face value in the receivable currency';

COMMENT ON COLUMN settlement_items.base_rate_monthly IS 'Base rate snapshot used in the formula';

COMMENT ON COLUMN settlement_items.spread_monthly IS 'Risk spread snapshot used in the formula';

COMMENT ON COLUMN settlement_items.term_months IS 'Term in months (calendar days / 30)';

COMMENT ON COLUMN settlement_items.present_value IS 'Present value in the receivable currency';

COMMENT ON COLUMN settlement_items.discount_amount IS 'Desagio in the receivable currency (face - present)';

COMMENT ON COLUMN settlement_items.fx_rate IS 'FX rate applied to this item (null when same currency)';

COMMENT ON COLUMN settlement_items.present_value_payment IS 'Present value converted to the batch payment currency';

CREATE INDEX ix_settlement_items_settlement_id ON settlement_items (settlement_id);

INSERT INTO currencies (code, name, decimal_places) VALUES ('BRL', 'Brazilian Real', 2);

INSERT INTO currencies (code, name, decimal_places) VALUES ('USD', 'US Dollar', 2);

INSERT INTO receivable_types (code, name, monthly_spread, active) VALUES ('DUPLICATA', 'Duplicata Mercantil', 0.015, true);

INSERT INTO receivable_types (code, name, monthly_spread, active) VALUES ('CHEQUE', 'Cheque Pré-datado', 0.025, true);

INSERT INTO alembic_version (version_num) VALUES ('cf5cd043f352') RETURNING alembic_version.version_num;

COMMIT;
