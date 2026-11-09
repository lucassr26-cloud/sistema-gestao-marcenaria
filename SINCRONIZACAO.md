# Sincronização e backup na nuvem (passo a passo)

Serve para usar o sistema no celular e no computador com os **mesmos dados**, e ter **backup automático**.
Usa o Supabase, que tem plano gratuito. Você faz isso **uma única vez** (cerca de 10 minutos).

## 1. Criar o projeto na nuvem
1. Entre em **supabase.com** e crie uma conta (pode usar o login do GitHub ou do Google).
2. Clique em **New project**. Escolha um nome (ex.: `marcenaria`), crie uma **senha do banco** (guarde em lugar seguro) e em **Region** escolha **South America (São Paulo)**. Plano **Free**.
3. Espere uns 2 minutos até o projeto ficar pronto.

## 2. Preparar o banco
1. No menu da esquerda, abra **SQL Editor** e clique em **New query**.
2. Abra o arquivo `supabase.sql` deste projeto, copie **tudo**, cole e clique em **Run**.
3. Deve aparecer **Success**. (Esse arquivo cria as tabelas e a regra de segurança: cada conta só vê os próprios dados.)

## 3. Login por e-mail e senha
1. Vá em **Authentication → Sign In / Providers** e confira que **Email** está ligado.
2. Para entrar logo depois de criar a conta, desligue **Confirm email**. Se deixar ligado, o Supabase manda um e-mail e você precisa tocar no link antes do primeiro login.

## 4. Copiar os dois endereços
1. Vá em **Project Settings → API** (ou **API Keys**).
2. Copie o **Project URL** (começa com `https://` e termina em `.supabase.co`).
3. Copie a chave **anon public** (o texto comprido que começa com `eyJ`).
   Nunca use a chave `service_role`: ela é secreta.

## 5. Ligar o sistema
- No sistema, abra **Cadastros → Conta e backup**, cole o endereço e a chave, toque em **Salvar configuração** e depois em **Criar conta**.
- Seus dados deste aparelho vão para a nuvem.
- No outro aparelho, abra o mesmo endereço do sistema, cole o endereço e a chave (uma vez) e toque em **Entrar** com o mesmo e-mail e a mesma senha. Os dados aparecem.
- Se preferir não colar em cada aparelho, os dois valores podem ser gravados no arquivo `config.js` do projeto. A chave `anon` é pública por desenho, quem protege os dados é a regra de segurança do `supabase.sql`.

## Como funciona no dia a dia
- Tudo que você salva é enviado sozinho para a nuvem em poucos segundos. Sem internet, fica guardado no aparelho e é enviado quando a conexão voltar.
- Ao abrir o sistema ou voltar para a aba, ele busca a versão mais nova da nuvem.
- Se dois aparelhos mudaram ao mesmo tempo, o sistema mostra uma tela para você escolher qual versão manter. A versão que sai de cena vira backup.
- A nuvem guarda um backup por dia (os últimos 30) e um antes de qualquer troca. Em **Conta e backup** você restaura qualquer um.

## Cuidados
- Guarde bem o e-mail e a senha da conta. Sem eles não há como recuperar os dados da nuvem.
- Projetos gratuitos do Supabase podem ser **pausados** depois de cerca de uma semana sem acesso. Os dados continuam guardados: é só entrar no painel do Supabase e clicar em reativar.
- Continue fazendo, de vez em quando, o backup em arquivo ou texto (aba Estoque). É a segunda cópia, fora da nuvem.
