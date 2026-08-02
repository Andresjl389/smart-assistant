import logging
import re

import httpx

from app.shared.config.settings import settings


logger = logging.getLogger(__name__)


class EmailClassifier:
    labels = {
        "trabajo": "AI/Trabajo",
        "finanzas": "AI/Finanzas",
        "personal": "AI/Personal",
        "promociones": "AI/Promociones",
        "soporte": "AI/Soporte",
        "otros": "AI/Otros",
    }

    sender_rules = (
        ("linkedin.com", "trabajo"),
        ("ticjob", "trabajo"),
        ("computrabajo", "trabajo"),
        ("elempleo", "trabajo"),
        ("indeed", "trabajo"),
        ("getonbrd", "trabajo"),
        ("magneto365", "trabajo"),
        ("bancolombia", "finanzas"),
        ("davivienda", "finanzas"),
        ("nequi", "finanzas"),
        ("rappicard", "finanzas"),
        ("bbva", "finanzas"),
    )

    keyword_rules = (
        (
            "finanzas",
            (
                "factura",
                "pago",
                "banco",
                "pse",
                "transferencia",
                "transaccion",
                "bre-b",
                "extracto",
                "comprobante",
            ),
        ),
        (
            "trabajo",
            (
                "vacante",
                "empleo",
                "postulate",
                "postulacion",
                "contratando",
                "reclutamiento",
                "hiring",
                "job alert",
            ),
        ),
        (
            "promociones",
            (
                "descuento",
                "cupon",
                "cyber",
                "black friday",
                "rebaja",
                "promocion",
            ),
        ),
        (
            "soporte",
            (
                "soporte",
                "ticket",
                "support",
                "incidencia",
            ),
        ),
    )

    def classify(self, email: dict) -> str:
        return self.classify_batch([email])[0]

    def classify_batch(self, emails: list[dict]) -> list[str]:
        if not emails:
            return []

        categories: list[str | None] = [None] * len(emails)
        pending = []

        for index, email in enumerate(emails):
            if settings.AI_RULES_PREFILTER:
                rule_category = self._match_rules(email)

                if rule_category:
                    categories[index] = rule_category
                    continue

            pending.append(index)

        for chunk in self._chunked(pending, settings.AI_BATCH_SIZE):
            chunk_emails = [emails[index] for index in chunk]

            for position, category in enumerate(self._classify_chunk(chunk_emails)):
                categories[chunk[position]] = category

        return [
            self.labels.get(category or "otros", self.labels["otros"])
            for category in categories
        ]

    def _classify_chunk(self, emails: list[dict]) -> list[str]:
        provider = settings.AI_PROVIDER.lower()

        try:
            if provider == "openrouter":
                content = self._call_openrouter(emails)
            elif provider == "gemini":
                content = self._call_gemini(emails)
            else:
                raise ValueError(f"Proveedor de IA no soportado: {settings.AI_PROVIDER}")
        except Exception as error:
            logger.warning(
                "Clasificacion por IA fallo para %s correos, se usan reglas. Detalle: %s",
                len(emails),
                error,
            )
            return [self._classify_with_rules(email) for email in emails]

        return self._parse_batch_response(content, emails)

    def _call_openrouter(self, emails: list[dict]) -> str:
        response = httpx.post(
            f"{settings.OPENROUTER_BASE_URL}/chat/completions",
            headers=self._openrouter_headers(),
            json={
                "model": settings.OPENROUTER_MODEL,
                "temperature": 0,
                "max_tokens": len(emails) * 12 + 32,
                "messages": [
                    {
                        "role": "system",
                        "content": self._system_prompt(len(emails)),
                    },
                    {
                        "role": "user",
                        "content": self._batch_prompt(emails),
                    },
                ],
            },
            timeout=60,
        )

        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as error:
            raise RuntimeError(
                self._format_openrouter_error(error.response)
            ) from error

        return self._extract_openrouter_content(response.json())

    def _call_gemini(self, emails: list[dict]) -> str:
        from google import genai

        client = genai.Client(api_key=settings.gemini_api_key)
        response = client.models.generate_content(
            model=settings.GEMINI_MODEL,
            contents=(
                f"{self._system_prompt(len(emails))}\n\n{self._batch_prompt(emails)}"
            ),
        )

        return response.text or ""

    def _openrouter_headers(self):
        headers = {
            "Authorization": f"Bearer {settings.openrouter_api_key}",
            "Content-Type": "application/json",
            "X-Title": settings.OPENROUTER_SITE_NAME,
        }

        if settings.OPENROUTER_SITE_URL:
            headers["HTTP-Referer"] = settings.OPENROUTER_SITE_URL

        return headers

    def _system_prompt(self, total: int) -> str:
        categories = ", ".join(self.labels.keys())

        return (
            f"Clasifica {total} correos en una sola categoria cada uno. "
            f"Categorias validas: {categories}. "
            "Responde una linea por correo con el formato 'numero: categoria', "
            "en el mismo orden y sin texto adicional."
        )

    def _batch_prompt(self, emails: list[dict]) -> str:
        body_limit = 4000 if len(emails) == 1 else 500

        return "\n\n".join(
            f"[{index + 1}]{self._email_prompt(email, body_limit)}"
            for index, email in enumerate(emails)
        )

    def _email_prompt(self, email: dict, body_limit: int = 4000) -> str:
        return f"""
De: {email.get("from", "")}
Asunto: {email.get("subject", "")}
Resumen: {email.get("snippet", "")}
Cuerpo: {email.get("body", "")[:body_limit]}
"""

    def _parse_batch_response(self, content: str, emails: list[dict]) -> list[str]:
        parsed = {}

        for line in content.splitlines():
            match = re.match(r"\s*\[?(\d+)\]?\s*[:.)-]\s*(.+)", line)

            if not match:
                continue

            index = int(match.group(1)) - 1

            if 0 <= index < len(emails):
                parsed[index] = self._normalize_category(match.group(2))

        if not parsed and len(emails) == 1:
            parsed[0] = self._normalize_category(content)

        missing = len(emails) - len(parsed)

        if missing:
            logger.warning(
                "La IA no respondio %s de %s correos, se completan con reglas.",
                missing,
                len(emails),
            )

        return [
            parsed.get(index) or self._classify_with_rules(email)
            for index, email in enumerate(emails)
        ]

    def _normalize_category(self, text: str) -> str:
        category = text.strip().lower().strip(" .,:;`\"'")

        if category in self.labels:
            return category

        for valid_category in self.labels:
            if valid_category in category:
                return valid_category

        return "otros"

    def _extract_openrouter_content(self, data: dict) -> str:
        choices = data.get("choices") or []

        if not choices:
            return ""

        message = choices[0].get("message") or {}
        content = message.get("content")

        if isinstance(content, str):
            return content

        if isinstance(content, list):
            return " ".join(
                item.get("text", "")
                for item in content
                if isinstance(item, dict)
            )

        return ""

    def _match_rules(self, email: dict) -> str | None:
        sender = email.get("from", "").lower()

        for fragment, category in self.sender_rules:
            if fragment in sender:
                return category

        text = " ".join(
            [
                email.get("subject", ""),
                email.get("snippet", ""),
            ]
        ).lower()

        for category, keywords in self.keyword_rules:
            if any(keyword in text for keyword in keywords):
                return category

        return None

    def _classify_with_rules(self, email: dict) -> str:
        return self._match_rules(email) or "otros"

    def _chunked(self, items: list, size: int):
        step = max(size, 1)

        for start in range(0, len(items), step):
            yield items[start : start + step]

    def _format_openrouter_error(self, response: httpx.Response) -> str:
        try:
            error_data = response.json()
        except ValueError:
            error_data = response.text

        if response.status_code == 401:
            return (
                "OpenRouter rechazo la API key. Revisa OPENROUTER_API_KEY "
                "en .env; debe ser una key de OpenRouter tipo sk-or-v1. "
                f"Detalle: {error_data}"
            )

        if response.status_code == 429:
            return f"OpenRouter alcanzo limite de cuota o rate limit. Detalle: {error_data}"

        return f"OpenRouter error {response.status_code}: {error_data}"
