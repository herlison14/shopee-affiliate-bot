# Contribuindo — ShopeeViral.AI

Checklist a seguir **antes de todo commit/push** em `backend/` ou `frontend/`. Baseado em bugs reais que já passaram batido (conflitos de dependência só visíveis no Python 3.11 do Render, bcrypt incompatível, JSX em arquivo `.js`, timestamps timezone-aware vs naive).

## Backend (`backend/`)

1. **Sintaxe**: `python -m py_compile <arquivos alterados>` antes de qualquer coisa.
2. **Testes**: rodar a suíte completa, não só o teste novo.
   ```bash
   cd backend
   python -m venv .venv_check
   .venv_check/Scripts/python -m pip install -r requirements-dev.txt
   .venv_check/Scripts/python -m pytest tests/ -q
   ```
   - `psycopg2-binary` pode falhar de instalar localmente se a sua máquina não estiver no Python 3.11 (o que o Render usa, via `runtime.txt`). Isso é esperado — pule esse pacote no venv de teste local, ele não afeta a lógica que os testes exercitam.
   - Sempre que adicionar/mudar uma dependência, valide a resolução com o **arquivo `requirements.txt` real** (não uma lista de pacotes solta digitada na hora) — já aconteceu de uma combinação solta resolver localmente e o arquivo pinado real conflitar no Render.
3. **Migration nova?** Toda mudança de schema precisa de um arquivo em `alembic/versions/`, com `down_revision` apontando pra migration anterior (não esquecer de encadear).
4. **Limpar antes de comitar**: `rm -rf .venv_check __pycache__ */__pycache__ test.db`

## Frontend (`frontend/`)

1. `npm run build` tem que passar limpo antes de comitar.
2. Arquivo com JSX precisa de extensão `.jsx`, nunca `.js` (o build do Vercel falha silenciosamente diferente do dev local).

## Depois do push

- O Render tem auto-deploy no push pra `main`. Acompanhar via API (`GET /v1/services/{id}/deploys`) até `status: live` — não assumir que passou só porque o push funcionou.
- Mudar uma env var no Render **não reinicia o serviço automaticamente** — precisa disparar `POST /v1/services/{id}/deploys` depois.
- Depois de `live`, validar com uma chamada real (`/health`, e pelo menos um fluxo ponta a ponta tocando o banco) — build verde não significa app funcionando.

## Operações destrutivas

Nunca fazer sem confirmação explícita do usuário antes:
- `git push --force` / reescrever histórico (`git filter-repo`, `git rebase`)
- `git reset --hard`
- Apagar banco de dados ou tabelas
- Editar `requirements.txt` removendo pins sem testar a resolução completa primeiro

## CLAUDE.md — atualizar junto de todo commit relevante

Sempre que um commit mudar arquitetura, decisão técnica ou comportamento de algo descrito
na seção "ShopeeViral.AI" do [CLAUDE.md](./CLAUDE.md) (ex: nova feature do backend/frontend,
mudança de estratégia como a decisão de não automatizar navegação na Shopee, novo
endpoint/rota pública), **atualizar o CLAUDE.md no mesmo commit** (ou em commit imediatamente
seguinte) e dar push junto. Não deixar o CLAUDE.md desatualizado em relação ao código.

Commits que são só limpeza/refactor sem mudança de comportamento não precisam tocar o
CLAUDE.md.

## Memória do projeto

Decisões e pendências de negócio (chaves de API, integrações externas, prazos) ficam documentadas no sistema de memória do Claude, não aqui. Este arquivo é só sobre *como* validar uma mudança de código antes de subir.
