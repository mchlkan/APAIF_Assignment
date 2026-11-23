-- Books to Scrape: database schema for Supabase (Postgres).
-- Run once in the Supabase dashboard: SQL Editor → New query → paste → Run.
-- Safe to run again: it only creates what is missing and recreates the policies.

-- ---------------------------------------------------------------- tables

create table if not exists public.categories (
  id   bigint generated always as identity primary key,
  name text not null unique
);

create table if not exists public.books (
  upc            text primary key,                 -- the site's own unique product code
  title          text not null,
  category_id    bigint not null references public.categories (id),
  price          numeric(8, 2) not null,           -- GBP, incl. tax
  price_excl_tax numeric(8, 2),
  tax            numeric(8, 2),
  in_stock       boolean not null,
  stock_count    integer,                          -- the "(22 available)" number
  rating         smallint not null check (rating between 1 and 5),
  description    text,
  image_url      text,
  product_url    text not null unique,
  first_seen     timestamptz not null default now(),  -- scraper never sends it, so an upsert keeps the original
  last_scraped   timestamptz not null
);

-- The app filters and groups by category.
create index if not exists books_category_id_idx on public.books (category_id);

create table if not exists public.scrape_runs (
  id            bigint generated always as identity primary key,
  started_at    timestamptz not null default now(),
  finished_at   timestamptz,
  mode          text not null check (mode in ('incremental', 'full')),
  pages_visited integer not null default 0,
  books_new     integer not null default 0,
  books_updated integer not null default 0,
  books_skipped integer not null default 0,
  errors        integer not null default 0,
  status        text not null default 'running' check (status in ('running', 'ok', 'failed'))
);

-- ---------------------------------------------------------------- access
-- Two keys, two roles:
--   publishable key → role "anon"         (the app)     → may only read
--   secret key      → role "service_role" (the scraper) → may write; it bypasses RLS
-- Grants are explicit so this works whether or not the project exposes new tables
-- to the Data API automatically.

grant usage on schema public to anon, authenticated, service_role;

grant select on public.categories, public.books, public.scrape_runs to anon, authenticated;
grant select, insert, update, delete on public.categories, public.books, public.scrape_runs to service_role;

-- Row Level Security: with RLS on, a role sees no rows unless a policy allows it.
-- There is a read policy only; with no insert/update/delete policy, the publishable key cannot change data.
alter table public.categories  enable row level security;
alter table public.books       enable row level security;
alter table public.scrape_runs enable row level security;

drop policy if exists "Public read" on public.categories;
create policy "Public read" on public.categories  for select to anon, authenticated using (true);

drop policy if exists "Public read" on public.books;
create policy "Public read" on public.books       for select to anon, authenticated using (true);

drop policy if exists "Public read" on public.scrape_runs;
create policy "Public read" on public.scrape_runs for select to anon, authenticated using (true);
