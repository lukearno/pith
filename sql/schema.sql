create table appuser (
  id                 serial primary key
, created            timestamp default now()
, doreset            boolean default true
, confirmed          boolean default false
, active             boolean default true
, lastactive         timestamp
, timezone           text
, role               text
);
create table appuser_pii (
  user_id            int primary key references appuser(id) on delete cascade
, password           text
, totp               bytea
, first_name         text
, last_name          text
, email              text unique
, email_hash         bytea
);
create table access_token (
  user_id            int primary key references appuser(id) on delete cascade
, token              bytea unique
, created            timestamp default now()
, used               int default 0
);
create table access_log (
  user_id            int primary key references appuser(id) on delete cascade
, accessed           timestamp default now()
);
