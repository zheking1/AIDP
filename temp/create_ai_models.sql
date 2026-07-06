CREATE TABLE IF NOT EXISTS ai_models (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(128) NOT NULL UNIQUE,
    display_name VARCHAR(256),
    provider VARCHAR(64) NOT NULL,
    model_id VARCHAR(128) NOT NULL,
    api_key TEXT,
    base_url VARCHAR(512),
    max_tokens INTEGER DEFAULT 4096,
    temperature DOUBLE PRECISION DEFAULT 0.7,
    timeout_secs INTEGER DEFAULT 60,
    is_active BOOLEAN DEFAULT true,
    is_default BOOLEAN DEFAULT false,
    extra_config JSONB DEFAULT '{}',
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

INSERT INTO ai_models (name, display_name, provider, model_id, base_url, is_active, is_default) VALUES
('gpt-4o', 'GPT-4o', 'openai', 'gpt-4o', 'https://api.openai.com/v1', false, false),
('gpt-4o-mini', 'GPT-4o Mini', 'openai', 'gpt-4o-mini', 'https://api.openai.com/v1', false, false),
('claude-3.5-sonnet', 'Claude 3.5 Sonnet', 'anthropic', 'claude-3-5-sonnet-20241022', 'https://api.anthropic.com', false, false),
('deepseek-chat', 'DeepSeek Chat', 'deepseek', 'deepseek-chat', 'https://api.deepseek.com', false, false),
('qwen-plus', 'Qwen Plus', 'alibaba', 'qwen-plus', 'https://dashscope.aliyuncs.com/compatible-mode/v1', false, false)
ON CONFLICT (name) DO NOTHING;
