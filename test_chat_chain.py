"""
Prueba de cadena conversacional — POST /recommendation/chat
Turno 1: "Recomiendame películas para ver con mis dos hijos pequeños"
Turno 2: "Vimos zootopia y nos gustó, recomiendame similares"
"""

import json
import sys
import requests

BASE = "http://localhost:8000/api/v1"
SESSION_ID = "test-session-chat-001"

# ── Credenciales ─────────────────────────────────────────────────────────────
# Ajusta email/password al usuario de prueba que tengas registrado

EMAIL = "demo@example.com"
PASSWORD = "Admin123"


def login() -> str:
    r = requests.post(f"{BASE}/auth/login", json={"email": EMAIL, "password": PASSWORD}, timeout=10)
    if r.status_code != 200:
        print(f"[ERROR] Login falló ({r.status_code}): {r.text}")
        sys.exit(1)
    token = r.json()["access_token"]
    print(f"[OK] Login exitoso\n")
    return token


def chat_turn(token: str, messages: list[dict]) -> dict:
    payload = {"session_id": SESSION_ID, "messages": messages}
    r = requests.post(
        f"{BASE}/recommendation/chat",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
        timeout=180,
    )
    if r.status_code != 200:
        print(f"[ERROR] Chat falló ({r.status_code}): {r.text}")
        sys.exit(1)
    return r.json()


def print_response(turn: int, data: dict):
    print(f"{'='*60}")
    print(f"TURNO {turn}")
    print(f"{'='*60}")
    print(f"Estrategia   : {data.get('strategy_used', '—')}")
    print(f"Turno #      : {data.get('turn_count', '—')}")
    print(f"Tiempo (ms)  : {data.get('execution_ms', '—')}")
    print(f"\nContexto extraído:")
    ctx = data.get("context_extracted", {})
    for k, v in ctx.items():
        if v is not None and v != [] and v != {}:
            print(f"  {k}: {v}")
    print(f"\nExplicación:\n  {data.get('explanation', '—')}\n")
    movies = data.get("movies", [])
    print(f"Películas recomendadas ({len(movies)}):")
    for i, m in enumerate(movies, 1):
        score = m.get("compatibilityScore", 0)
        rating = m.get("averageRating")
        genre = m.get("genreName", "")
        desc = m.get("description", "")
        print(f"  {i}. {m['title']} (score={score:.2f}{', R:'+str(rating) if rating else ''}{', '+genre if genre else ''})")
        if desc:
            print(f"     → {desc[:100]}{'...' if len(desc) > 100 else ''}")
    print()


def main():
    token = login()

    # ── Turno 1 ───────────────────────────────────────────────────────────────
    msg1 = "Recomiendame películas para ver con mis dos hijos pequeños"
    print(f"[Turno 1] Usuario: {msg1}\n")

    messages = [{"role": "user", "content": msg1}]
    resp1 = chat_turn(token, messages)
    print_response(1, resp1)

    # Construir historial acumulado con la respuesta del asistente
    assistant_reply = resp1.get("explanation", "")
    movies_list = ", ".join(m["title"] for m in resp1.get("movies", []))
    assistant_content = f"{assistant_reply} Películas sugeridas: {movies_list}"

    messages.append({"role": "assistant", "content": assistant_content})

    # ── Turno 2 ───────────────────────────────────────────────────────────────
    msg2 = "Vimos Zootopia y nos gustó, recomiendame similares"
    print(f"[Turno 2] Usuario: {msg2}\n")

    messages.append({"role": "user", "content": msg2})
    resp2 = chat_turn(token, messages)
    print_response(2, resp2)


if __name__ == "__main__":
    main()
