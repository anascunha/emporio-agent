"""Customer-facing interface text in English (default) and Portuguese.

Only the interface chrome changes: Mel herself answers in the language of each
customer message, whatever the interface language is.
"""

from __future__ import annotations

# Plain labels: flag emoji render as "GB"/"BR" letters on Windows.
LANGUAGES = {"en": "English", "pt": "Português"}

TEXT: dict[str, dict] = {
    "en": {
        "msgr": {"title": "Empório da Música", "status_idle": "online", "status_typing": "typing…", "placeholder": "Message"},
        "web": {"title": "Chat with Mel", "status_idle": "Online now", "status_typing": "Mel is typing…", "placeholder": "Type your message…"},
        "greeting": (
            "Hi! I'm **Mel**, Empório da Música's virtual assistant 🎸\n\n"
            "I can help you find an instrument, check an order or answer questions about the store. "
            "How can I help?"
        ),
        "quick_replies": ("Acoustic guitars under R$ 1.000", "My order status", "Store hours", "Returns and exchanges"),
        "day": "TODAY",
        "msgr_notice": "Mel is a virtual assistant · ask for a person anytime",
        "error": "⚠️ Couldn't reply right now. Please try again in a moment.",
        "unanswered": "Message not answered. Please send it again.",
        "powered": "Virtual assistant · answers based on the store's system",
        "hero": {
            "eyebrow": "Campo Grande · MS · since 2008",
            "tagline": "Sua música começa aqui. Your music starts here.",
            "facts": [
                ("STORE", "Rua 14 de Maio, 3200 · Centro"),
                ("HOURS", "Mon–Fri 9am–6pm · Sat 9am–1pm"),
                ("PAYMENT", "5% off with PIX · up to 12 interest-free installments"),
                ("DELIVERY", "Free over R$ 500 in Greater Campo Grande"),
            ],
            "cta": "Questions about instruments, orders or returns? <strong>Chat with Mel</strong>, our virtual assistant.",
        },
    },
    "pt": {
        "msgr": {"title": "Empório da Música", "status_idle": "online", "status_typing": "digitando…", "placeholder": "Mensagem"},
        "web": {"title": "Fale com a Mel", "status_idle": "Online agora", "status_typing": "Mel está digitando…", "placeholder": "Escreva sua mensagem…"},
        "greeting": (
            "Oi! Eu sou a **Mel**, assistente virtual da Empório da Música 🎸\n\n"
            "Posso te ajudar a encontrar um instrumento, ver o status de um pedido ou tirar "
            "dúvidas sobre a loja. Como posso ajudar?"
        ),
        "quick_replies": ("Ver violões até R$ 1.000", "Status do meu pedido", "Horário da loja", "Trocas e devoluções"),
        "day": "HOJE",
        "msgr_notice": "Atendimento virtual da Mel · peça um atendente quando quiser",
        "error": "⚠️ Não foi possível responder agora. Tente novamente em instantes.",
        "unanswered": "Mensagem não respondida. Envie novamente, por favor.",
        "powered": "Atendimento virtual · respostas com base no sistema da loja",
        "hero": {
            "eyebrow": "Campo Grande · MS · desde 2008",
            "tagline": "Sua música começa aqui.",
            "facts": [
                ("LOJA", "Rua 14 de Maio, 3200 · Centro"),
                ("HORÁRIO", "Seg a sex 9h às 18h · Sáb 9h às 13h"),
                ("PAGAMENTO", "5% off no PIX · até 12x sem juros"),
                ("ENTREGA", "Frete grátis acima de R$ 500 na Grande Campo Grande"),
            ],
            "cta": "Dúvidas sobre instrumentos, pedidos ou trocas? <strong>Fale com a Mel</strong>, nossa assistente virtual.",
        },
    },
}


def hero_html(lang: str) -> str:
    """Store-page block next to the website widget (trusted, static text)."""
    hero = TEXT[lang]["hero"]
    facts = "".join(f'<div class="fact"><b>{label}</b><span>{value}</span></div>' for label, value in hero["facts"])
    return (
        '<div class="web-hero">'
        f'<div class="eyebrow">{hero["eyebrow"]}</div>'
        "<h1>Empório da Música</h1>"
        f'<div class="tagline">{hero["tagline"]}</div>'
        f'<div class="facts">{facts}</div>'
        f'<div class="cta">{hero["cta"]}</div>'
        "</div>"
    )
