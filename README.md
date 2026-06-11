# ⚽ Copa do Mundo 2026 — Streamlit App

Dashboard para acompanhar a Copa do Mundo FIFA 2026 em tempo real.

## Funcionalidades

- 🔴 **Ao Vivo** — jogos em andamento com placar em tempo real
- 📅 **Jogos de Hoje** — partidas do dia com horário de Brasília
- 🇧🇷 **Jogos do Brasil** — acompanhe a Seleção no Grupo C
- 🗓️ **Todos os Jogos** — calendário completo com filtros
- 🏅 **Classificação** — tabela por grupo atualizada
- 📊 **Grupos** — visão geral dos 12 grupos

## API

Usa a API pública gratuita [worldcup26.ir](https://worldcup26.ir) — sem chave necessária.

## Deploy no Streamlit Cloud (gratuito)

1. Suba para um repositório GitHub:
   ```
   git init
   git add app.py requirements.txt README.md
   git commit -m "Copa 2026 app"
   git push origin main
   ```

2. Acesse [share.streamlit.io](https://share.streamlit.io)

3. Conecte seu GitHub e selecione o repo

4. Main file: `app.py`

5. ✅ Deploy!

## Rodar localmente

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Estrutura

```
copa2026/
├── app.py            # App principal
├── requirements.txt  # Dependências
└── README.md
```
