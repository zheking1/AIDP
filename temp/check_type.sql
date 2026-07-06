SELECT pg_typeof(value), value::text FROM system_settings WHERE key = 'auth.allow_registration';
