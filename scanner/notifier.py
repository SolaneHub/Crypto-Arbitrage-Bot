import os
import requests
from datetime import datetime
from typing import Dict, Any, Optional
from dotenv import load_dotenv

load_dotenv()

class MarketNotifier:
    """
    Gestore centralizzato delle notifiche per Discord e Telegram.
    Utilizza Webhook Discord nativo per embed ricchi e interattivi,
    e Telegram Bot API come canale opzionale.
    """

    def __init__(self):
        self.discord_webhook = os.getenv("DISCORD_WEBHOOK_URL")
        self.telegram_token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID")

    def notify_startup(self, wallet_address: str, contract_address: str, balance_eur: float, eth_bal: float, mode: str = "LIVE"):
        """Invia notifica di avvio del bot su Discord / Telegram."""
        title = f"🟢 Arbitrage Bot Avviato [{mode}]"
        desc = (
            f"Il bot di arbitraggio è attivo e monitora le pool su **Base L2**.\n"
            f"• **Smart Contract**: [`{contract_address[:10]}...{contract_address[-6:]}`](https://basescan.org/address/{contract_address})\n"
            f"• **Wallet Gas**: `{wallet_address[:10]}...{wallet_address[-6:]}`\n"
            f"• **Saldo Iniziale**: **{balance_eur:.2f} €** ({eth_bal:.5f} ETH)"
        )
        
        # Invia a Discord
        self.send_discord_embed(
            title=title,
            description=desc,
            color=0x3498DB, # Blu
            fields=[
                {"name": "Rete", "value": "Base Mainnet (8453)", "inline": True},
                {"name": "Protezione", "value": "eth_call Pre-Flight", "inline": True},
                {"name": "Flash Loan", "value": "Aave V3 ($250 - $1.000)", "inline": True}
            ]
        )

    def notify_trade_executed(
        self,
        pair: str,
        buy_dex: str,
        sell_dex: str,
        flash_loan_usd: float,
        net_profit_eur: float,
        net_profit_usd: float,
        gas_cost_eur: float,
        wallet_total_eur: float,
        tx_hash: str,
        basescan_url: str
    ):
        """Invia notifica ricca con embed per trade on-chain confermato."""
        title = f"💰 ARBITRAGGIO LIVE CONFERMATO: +{net_profit_eur:.4f} €"
        desc = (
            f"Un'opportunità di arbitraggio atomico è stata completata con successo on-chain!\n"
            f"L'utile netto è già stato accreditato direttamente nel tuo portafoglio."
        )

        fields = [
            {"name": "Coppia", "value": f"**{pair}**", "inline": True},
            {"name": "Percorso DEX", "value": f"{buy_dex} ➡️ {sell_dex}", "inline": True},
            {"name": "Flash Loan Aave", "value": f"${flash_loan_usd:.0f} USD", "inline": True},
            {"name": "💵 Utile Netto", "value": f"**+{net_profit_eur:.4f} €** (+${net_profit_usd:.4f})", "inline": True},
            {"name": "⛽ Gas Base Speso", "value": f"{gas_cost_eur:.5f} €", "inline": True},
            {"name": "🏦 Saldo Portafoglio", "value": f"**{wallet_total_eur:.2f} €**", "inline": True},
            {"name": "🔗 Transazione On-Chain", "value": f"[Visualizza su Basescan Explorer]({basescan_url})", "inline": False}
        ]

        # 0x2ECC71 = Verde smeraldo
        self.send_discord_embed(
            title=title,
            description=desc,
            color=0x2ECC71,
            fields=fields
        )

        # Invia anche a Telegram se configurato
        tg_text = (
            f"🚀 <b>ARBITRAGGIO LIVE CONFERMATO!</b>\n\n"
            f"Coppia: <b>{pair}</b>\n"
            f"Percorso: {buy_dex} ➡️ {sell_dex}\n"
            f"Flash Loan: <b>${flash_loan_usd:.0f}</b>\n"
            f"Utile Netto: <b>+{net_profit_eur:.4f} €</b>\n"
            f"Gas: {gas_cost_eur:.5f} €\n"
            f"Saldo Portafoglio: <b>{wallet_total_eur:.2f} €</b>\n\n"
            f"<a href='{basescan_url}'>Basescan Explorer</a>"
        )
        self.send_telegram_text(tg_text)

    def send_discord_embed(
        self,
        title: str,
        description: str,
        color: int = 0x2ECC71,
        fields: Optional[list] = None
    ):
        """Invia un messaggio formattato con embed ricco su Discord via Webhook."""
        webhook_url = self.discord_webhook or os.getenv("DISCORD_WEBHOOK_URL")
        if not webhook_url:
            return

        embed = {
            "title": title,
            "description": description,
            "color": color,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "footer": {
                "text": "Base L2 Arbitrage Bot • Protezione Atomica Attiva"
            }
        }
        if fields:
            embed["fields"] = fields

        payload = {
            "username": "Crypto Arbitrage Bot",
            "avatar_url": "https://raw.githubusercontent.com/trustwallet/assets/master/blockchains/base/info/logo.png",
            "embeds": [embed]
        }

        try:
            requests.post(webhook_url, json=payload, timeout=6)
        except Exception:
            pass

    def send_telegram_text(self, text: str):
        """Invia notifica Telegram se configurata."""
        token = self.telegram_token or os.getenv("TELEGRAM_BOT_TOKEN")
        chat_id = self.telegram_chat_id or os.getenv("TELEGRAM_CHAT_ID")
        if not token or not chat_id:
            return

        try:
            url = f"https://api.telegram.org/bot{token}/sendMessage"
            payload = {
                "chat_id": chat_id,
                "text": text,
                "parse_mode": "HTML",
                "disable_web_page_preview": True
            }
            requests.post(url, json=payload, timeout=5)
        except Exception:
            pass

    def test_discord_connection(self) -> bool:
        """Invia un messaggio di test per verificare che il Webhook funzioni."""
        webhook_url = self.discord_webhook or os.getenv("DISCORD_WEBHOOK_URL")
        if not webhook_url:
            return False

        payload = {
            "username": "Crypto Arbitrage Bot",
            "avatar_url": "https://raw.githubusercontent.com/trustwallet/assets/master/blockchains/base/info/logo.png",
            "embeds": [{
                "title": "🎉 Collegamento Discord Riuscito con Successo!",
                "description": "Il canale Discord è ora configurato per ricevere tutti gli avvisi del Bot di Arbitraggio in tempo reale.",
                "color": 0x2ECC71,
                "fields": [
                    {"name": "Stato", "value": "🟢 Connesso e Pronto", "inline": True},
                    {"name": "Rete", "value": "Base Mainnet L2", "inline": True}
                ],
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }]
        }
        try:
            resp = requests.post(webhook_url, json=payload, timeout=6)
            return resp.status_code in (200, 204)
        except Exception:
            return False
