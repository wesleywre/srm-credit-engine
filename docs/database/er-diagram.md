# Modelo de Dados — SRM Credit Engine

Modelo relacional (PostgreSQL 16) que sustenta a precificação e liquidação de recebíveis multimoedas. O DDL completo está em [`ddl.sql`](./ddl.sql), gerado a partir das migrations Alembic.

## Diagrama ER

```mermaid
erDiagram
    currencies {
        varchar(3) code PK "ISO 4217 (BRL, USD)"
        varchar(50) name
        smallint decimal_places "precisão de arredondamento"
    }

    exchange_rates {
        uuid id PK
        varchar(3) base_currency_code FK
        varchar(3) quote_currency_code FK
        numeric(20_10) rate "quote por 1 unidade de base"
        varchar(30) source "MANUAL | MOCK_PROVIDER"
        timestamptz effective_at "vigência (histórico versionado)"
    }

    base_rates {
        uuid id PK
        varchar(3) currency_code FK
        numeric(10_6) monthly_rate "taxa base mensal (0.01 = 1%)"
        timestamptz effective_at "vigência (histórico versionado)"
    }

    receivable_types {
        int id PK
        varchar(30) code UK "DUPLICATA | CHEQUE"
        varchar(80) name
        numeric(10_6) monthly_spread "spread de risco mensal"
        boolean active
    }

    assignors {
        uuid id PK
        varchar(120) name
        varchar(14) document UK "CNPJ (somente dígitos)"
    }

    batches {
        uuid id PK
        uuid assignor_id FK
        varchar(3) payment_currency_code FK
        varchar(20) status "PENDING -> SETTLED"
        int version "optimistic locking"
    }

    receivables {
        uuid id PK
        uuid batch_id FK
        int receivable_type_id FK
        numeric(18_2) face_value "valor de face (> 0)"
        varchar(3) currency_code FK
        date due_date
    }

    settlements {
        uuid id PK
        uuid batch_id FK,UK "1 liquidacao por lote"
        varchar(3) payment_currency_code FK
        numeric(20_10) fx_rate "nulo quando mesma moeda"
        uuid fx_rate_id FK "proveniencia da taxa"
        numeric(18_2) total_face_value "na moeda de pagamento"
        numeric(18_2) total_present_value "na moeda de pagamento"
        numeric(18_2) total_discount "desagio total"
        timestamptz settled_at
    }

    settlement_items {
        uuid id PK
        uuid settlement_id FK
        uuid receivable_id FK,UK
        numeric(18_2) face_value "snapshot"
        varchar(3) currency_code FK
        numeric(10_6) base_rate_monthly "snapshot"
        numeric(10_6) spread_monthly "snapshot"
        numeric(10_4) term_months "dias corridos / 30"
        numeric(18_2) present_value "na moeda do titulo"
        numeric(18_2) discount_amount "desagio do item"
        numeric(20_10) fx_rate "snapshot (nulo se mesma moeda)"
        numeric(18_2) present_value_payment "convertido p/ moeda de pagamento"
    }

    currencies ||--o{ exchange_rates : "base / quote"
    currencies ||--o{ base_rates : "taxa base"
    currencies ||--o{ batches : "moeda de pagamento"
    currencies ||--o{ receivables : "moeda do titulo"
    assignors ||--o{ batches : "cede"
    batches ||--|{ receivables : "contem"
    receivable_types ||--o{ receivables : "classifica"
    batches ||--o| settlements : "liquidado por"
    exchange_rates ||--o{ settlements : "proveniencia FX"
    settlements ||--|{ settlement_items : "detalha"
    receivables ||--o| settlement_items : "precificado como"
```

## Decisões de modelagem

1. **Dinheiro e taxas em `NUMERIC`, nunca float** — `NUMERIC(18,2)` para valores monetários, `NUMERIC(20,10)` para taxas de câmbio e `NUMERIC(10,6)` para taxas mensais. Toda aritmética na aplicação usa `Decimal`.
2. **Taxas versionadas por vigência** — `exchange_rates` e `base_rates` são *append-only*: cada atualização insere um novo registro com `effective_at`, preservando o histórico para auditoria (a taxa vigente é a de maior `effective_at`). Unicidade por `(par, effective_at)` impede ticks duplicados.
3. **Snapshot completo na liquidação** — `settlement_items` grava **todos os insumos da fórmula** (taxa base, spread, prazo, taxa FX) no momento da liquidação. Uma liquidação passada permanece explicável mesmo que taxas e spreads mudem depois — exigência típica de auditoria em FIDC.
4. **Optimistic locking** — `batches.version` é o token de controle de concorrência: a liquidação só progride se a versão lida ainda for a corrente (`UPDATE ... WHERE version = :v`), evitando liquidação dupla sem lock pessimista.
5. **Spread data-driven + Strategy no código** — o spread mora em `receivable_types` (negócio ajusta sem deploy); a *forma* do cálculo é selecionada por Strategy Pattern no domínio, chaveada pelo `code` do tipo.
6. **Status com CHECK constraint** (`PENDING`/`SETTLED`) em vez de enum nativo do Postgres — evolução de valores sem `ALTER TYPE`, mantendo integridade no banco.
7. **Imutabilidade** — `settlements`/`settlement_items` não têm `updated_at`: são registros contábeis imutáveis por design; correções geram eventos novos, nunca updates.
