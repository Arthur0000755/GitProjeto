# 🤖 PromoBot — Bot de promoções para Telegram

Bot em Python que monitora produtos em vários marketplaces e avisa no Telegram
quando aparece uma promoção. Feito para rodar 24h em um servidor caseiro
(Raspberry Pi, mini PC, NAS etc.) via Docker ou systemd.

## Marketplaces suportados

| Loja | Como funciona | Credenciais |
|------|---------------|-------------|
| 🟡 **Mercado Livre** | API oficial de busca (`api.mercadolibre.com`) | App em [developers.mercadolivre.com.br](https://developers.mercadolivre.com.br) (Client ID/Secret). A API costuma recusar buscas sem autenticação. |
| 🟠 **Shopee** | Open API de afiliados (GraphQL), links já com sua comissão | AppID + Secret em [affiliate.shopee.com.br](https://affiliate.shopee.com.br) → Open API |
| 📦 **Amazon** | Product Advertising API 5.0 (assinatura SigV4), links com sua tag | Access Key, Secret Key e Partner Tag do [Associados](https://associados.amazon.com.br) |
| 🔴 **AliExpress** | API de afiliados (`aliexpress.affiliate.product.query`) | App Key/Secret em [openservice.aliexpress.com](https://openservice.aliexpress.com) |
| 📰 **Outras lojas** | Qualquer feed RSS/Atom (agregadores de promoções, blogs, lojas) — preços extraídos de textos como "De R$ 199,90 por R$ 129,90" | Nenhuma, só as URLs |

Cada loja só é ativada se as credenciais estiverem no `.env`. Uma loja fora do ar
não atrapalha as outras.

> Observação: as APIs oficiais mudam com frequência (a Amazon, por exemplo, vem
> migrando a PA-API para uma nova API de criadores). Cada loja fica num arquivo
> separado em `promobot/sources/`, então é fácil ajustar ou adicionar novas.

## Comandos

| Comando | O que faz |
|---------|-----------|
| `/add iphone 15 4500` | Monitora "iphone 15" com preço máximo de R$ 4.500 (o preço é opcional) |
| `/remove iphone 15` ou `/remove 3` | Para de monitorar (por termo ou id) |
| `/lista` | Produtos monitorados |
| `/buscar air fryer` | Busca agora em todas as lojas e mostra os maiores descontos |
| `/desconto 30` | Só alerta ofertas com pelo menos 30% de desconto |
| `/pausar` / `/retomar` | Pausa/retoma os alertas do chat |
| `/verificar` | Força uma verificação imediata |
| `/status` | Fontes ativas, intervalo e seu ID do Telegram |

Como funciona a verificação: a cada `CHECK_INTERVAL_MINUTES` o bot busca cada termo
monitorado em todas as lojas, filtra pelas palavras do termo, desconto mínimo e
preço máximo, e envia até 5 ofertas por termo (com foto). Ofertas já enviadas são
guardadas em SQLite e só são reenviadas se o preço cair mais 5%. Se
`TELEGRAM_CHANNEL_ID` estiver definido, os alertas também vão para o canal.

## Instalação

### 1. Criar o bot no Telegram
1. Fale com o [@BotFather](https://t.me/BotFather) → `/newbot` → copie o token.
2. Descubra seu ID com o [@userinfobot](https://t.me/userinfobot).

### 2. Configurar
```bash
git clone https://github.com/arthur0000755/gitprojeto.git promobot
cd promobot
cp .env.example .env
nano .env   # preencha TELEGRAM_BOT_TOKEN, ADMIN_IDS e as credenciais das lojas
```

### 3a. Rodar com Docker (recomendado)
```bash
docker compose up -d --build
docker compose logs -f
```
O banco fica em `./data` e o container reinicia sozinho se o servidor reiniciar.

### 3b. Rodar sem Docker (systemd)
```bash
sudo useradd -r -m -d /opt/promobot promobot
sudo cp -r . /opt/promobot && sudo chown -R promobot: /opt/promobot
cd /opt/promobot
sudo -u promobot python3 -m venv .venv
sudo -u promobot .venv/bin/pip install -r requirements.txt
sudo cp deploy/promobot.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now promobot
journalctl -u promobot -f
```

### Rodar manualmente (teste)
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m promobot
```

O bot usa *long polling*, então **não precisa abrir portas** no roteador nem ter
IP fixo.

## Desenvolvimento

```bash
pip install -r requirements-dev.txt
pytest
```

Para adicionar uma loja nova, crie uma classe em `promobot/sources/` que herde de
`Source` e implemente `async def search(self, keyword) -> list[Deal]`, depois
registre-a em `promobot/sources/__init__.py`.

```
promobot/
├── __main__.py      # ponto de entrada (python -m promobot)
├── bot.py           # comandos do Telegram e verificação periódica
├── config.py        # leitura do .env
├── db.py            # SQLite: termos monitorados, ofertas enviadas
├── formatting.py    # mensagens em HTML
├── monitor.py       # busca paralela + filtros
└── sources/         # um arquivo por marketplace
```
