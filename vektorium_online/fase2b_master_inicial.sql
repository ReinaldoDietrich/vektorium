-- ============================================================
-- VEKTORIUM — Master inicial (Reinaldo)
-- Rodar DEPOIS de:
--   1. fase2_auth_rls.sql aplicado
--   2. Você ter criado a conta reinaldo.dietrich@gmail.com no Supabase
--      (Authentication → Users → Add user → Send invite OU Create user)
-- ============================================================

-- Promove reinaldo.dietrich@gmail.com a MASTER + assinatura VITALÍCIA
UPDATE public.usuarios
   SET papel = 'master'
 WHERE email = 'reinaldo.dietrich@gmail.com';

UPDATE public.assinaturas
   SET status = 'active',
       plano  = 'vitalicio',
       vence_em = NULL,
       atualizado_em = NOW()
 WHERE usuario_id = (SELECT id FROM public.usuarios
                      WHERE email = 'reinaldo.dietrich@gmail.com');

-- Verificação
SELECT u.email, u.papel, a.status, a.plano, a.vence_em
  FROM public.usuarios u
  LEFT JOIN public.assinaturas a ON a.usuario_id = u.id
 WHERE u.email = 'reinaldo.dietrich@gmail.com';
