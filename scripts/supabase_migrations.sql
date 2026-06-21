-- =====================================================================================
-- APEXTIP AI - DATABASE MIGRATION SCRIPT (SUPABASE / POSTGRESQL)
-- =====================================================================================
-- Propósito: Crea la estructura relacional necesaria para almacenar las predicciones,
-- el historial de cuotas (Line Reversals), perfiles de tipsters y relaciones sociales.
-- Ejecutar en: Supabase SQL Editor
-- =====================================================================================

-- 1. Tabla de Perfiles (Sincronizada con Firebase Auth)
CREATE TABLE IF NOT EXISTS profiles (
    id UUID PRIMARY KEY, -- Coincide con Firebase UID (UUID format o parseado)
    email VARCHAR(255) NOT NULL UNIQUE,
    username VARCHAR(100) UNIQUE,
    role VARCHAR(20) DEFAULT 'user' CHECK (role IN ('user', 'tipster', 'admin')),
    subscription_status VARCHAR(20) DEFAULT 'free' CHECK (subscription_status IN ('free', 'premium')),
    
    -- Métricas de rendimiento para Tipsters
    win_rate NUMERIC(5,2) DEFAULT 0.00,
    yield_percentage NUMERIC(6,2) DEFAULT 0.00,
    followers_count INT DEFAULT 0,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, NOW()) NOT NULL
);

-- 2. Sistema Social (Followers)
CREATE TABLE IF NOT EXISTS followers (
    follower_id UUID REFERENCES profiles(id) ON DELETE CASCADE,
    following_id UUID REFERENCES profiles(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, NOW()) NOT NULL,
    PRIMARY KEY (follower_id, following_id)
);

-- 3. Historial de Cuotas (Para detectar Line Reversal / Sharp Money)
CREATE TABLE IF NOT EXISTS odds_history (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    fixture_id VARCHAR(50) NOT NULL,
    bookmaker_id INT NOT NULL, -- ID de la casa de apuestas (ej. 1 = 10Bet/Bet365)
    
    -- Líneas de Dinero (Mercado Principal 1X2)
    quota_home NUMERIC(6,2) NOT NULL,
    quota_draw NUMERIC(6,2) NOT NULL,
    quota_away NUMERIC(6,2) NOT NULL,
    
    recorded_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, NOW()) NOT NULL
);

-- Índice para acelerar la búsqueda de historial de un partido específico
CREATE INDEX IF NOT EXISTS idx_odds_history_fixture ON odds_history(fixture_id, recorded_at);

-- 4. Predicciones Masticadas de la Inteligencia Artificial (Cerebro ZCode)
CREATE TABLE IF NOT EXISTS ai_predictions (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    fixture_id VARCHAR(50) NOT NULL UNIQUE,
    sport VARCHAR(30) NOT NULL,
    event_name VARCHAR(150) NOT NULL, -- Ej: Real Madrid vs Barcelona
    league_name VARCHAR(255) DEFAULT 'Unknown',
    event_date TIMESTAMP WITH TIME ZONE NOT NULL,
    
    -- Métricas del Sistema ApexTip AI
    apex_velocity_home INT NOT NULL, -- Fuerza local (1-100)
    apex_velocity_away INT NOT NULL, -- Fuerza visitante (1-100)
    
    -- El Pick Masticado por Gemini (ApexTip AI)
    strategy VARCHAR(50) NOT NULL,
    selected_market VARCHAR(100) NOT NULL,
    recommended_quota NUMERIC(6,2) NOT NULL,
    stake NUMERIC(5,2) DEFAULT 1.0,
    main_pick_confidence INT NOT NULL CHECK (main_pick_confidence BETWEEN 1 AND 100),
    confidence_winner INT NOT NULL CHECK (confidence_winner BETWEEN 1 AND 100),
    confidence_over INT NOT NULL CHECK (confidence_over BETWEEN 1 AND 100),
    confidence_corners INT NOT NULL CHECK (confidence_corners BETWEEN 1 AND 100),
    confidence_btts INT NOT NULL CHECK (confidence_btts BETWEEN 1 AND 100),
    ai_justification TEXT NOT NULL, -- Análisis digerido para el usuario
    
    -- Control de Acceso y Origen
    tier VARCHAR(20) DEFAULT 'premium',
    is_top_match BOOLEAN DEFAULT FALSE,
    
    -- Control de Estado (Lifecycle)
    status VARCHAR(20) DEFAULT 'unconfirmed' CHECK (status IN ('unconfirmed', 'pending', 'won', 'lost', 'void')), 
    pnl NUMERIC(10,2) DEFAULT NULL,
    
    -- Metadatos
    created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, NOW()) NOT NULL
);

-- Índices analíticos para búsquedas rápidas por fecha desde Flutter
CREATE INDEX IF NOT EXISTS idx_predictions_date ON ai_predictions(event_date);
CREATE INDEX IF NOT EXISTS idx_predictions_status ON ai_predictions(status);

-- 5. Publicaciones de la Comunidad (Feed de Tipsters)
CREATE TABLE IF NOT EXISTS community_posts (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    author_id UUID REFERENCES profiles(id) ON DELETE CASCADE,
    fixture_id VARCHAR(50),
    content TEXT NOT NULL,
    
    -- Elementos ocultables (Ofuscación Premium)
    market VARCHAR(100),
    recommended_odds NUMERIC(6,2),
    is_premium_only BOOLEAN DEFAULT FALSE,
    
    likes_count INT DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, NOW()) NOT NULL
);
