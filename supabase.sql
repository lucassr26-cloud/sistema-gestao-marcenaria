-- Preparação do banco para a sincronização do Sistema de Gestão de Marcenaria.
-- Cole este arquivo inteiro no SQL Editor do Supabase e clique em Run. Pode rodar mais de uma vez sem problema.

-- 1) Os dados de cada usuário (um registro por conta). "versao" evita que um aparelho apague o que o outro salvou.
create table if not exists public.ljwa_dados (
  user_id uuid primary key references auth.users (id) on delete cascade,
  conteudo jsonb not null,
  versao bigint not null default 1,
  atualizado_em timestamptz not null default now()
);

-- 2) Backups (uma cópia por dia, as últimas 30, e uma antes de qualquer troca de versão)
create table if not exists public.ljwa_backups (
  id bigint generated always as identity primary key,
  user_id uuid not null default auth.uid() references auth.users (id) on delete cascade,
  criado_em timestamptz not null default now(),
  motivo text,
  conteudo jsonb not null
);
create index if not exists ljwa_backups_user_data on public.ljwa_backups (user_id, criado_em desc);

-- 3) Segurança: cada pessoa só enxerga e altera os próprios dados
alter table public.ljwa_dados enable row level security;
alter table public.ljwa_backups enable row level security;

drop policy if exists "dados: ler os proprios" on public.ljwa_dados;
drop policy if exists "dados: criar os proprios" on public.ljwa_dados;
drop policy if exists "dados: atualizar os proprios" on public.ljwa_dados;
create policy "dados: ler os proprios" on public.ljwa_dados for select using (auth.uid() = user_id);
create policy "dados: criar os proprios" on public.ljwa_dados for insert with check (auth.uid() = user_id);
create policy "dados: atualizar os proprios" on public.ljwa_dados for update using (auth.uid() = user_id) with check (auth.uid() = user_id);

drop policy if exists "backups: ler os proprios" on public.ljwa_backups;
drop policy if exists "backups: criar os proprios" on public.ljwa_backups;
drop policy if exists "backups: apagar os proprios" on public.ljwa_backups;
create policy "backups: ler os proprios" on public.ljwa_backups for select using (auth.uid() = user_id);
create policy "backups: criar os proprios" on public.ljwa_backups for insert with check (auth.uid() = user_id);
create policy "backups: apagar os proprios" on public.ljwa_backups for delete using (auth.uid() = user_id);
