-- supabase_schema.sql
create table if not exists posts (
  id bigserial primary key,
  platform text,
  source_name text,
  source_url text,
  post_id text,
  post_url text,
  author text,
  text text,
  language text,
  datetime_utc timestamptz,
  datetime_local text,
  admin_area text,
  locality text,
  geofenced_area text,
  tension_level text,
  media_urls text,
  shares text,
  likes text,
  comments text,
  collected_at_utc timestamptz default now(),
  collector text,
  hash text unique,
  notes text
);
create index if not exists idx_posts_platform on posts(platform);
create index if not exists idx_posts_datetime on posts(datetime_utc);
create index if not exists idx_posts_tension on posts(tension_level);
