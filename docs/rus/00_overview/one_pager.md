# DETM: One Pager (RU)

## Что это

DETM (Discrete Entropy-Time Model) — исследовательский рантайм дискретной динамики на решетке.
Фокус: появление устойчивых локальных структур (инвариантов) из локальных правил переноса, подавления и внутреннего времени.

## Что это не

- не физическая теория;
- не "ИИ из коробки";
- не доказательство универсальных законов.

Это инженерная и исследовательская платформа для проверяемых гипотез о самоорганизации.

## Канонические слои

- `detm/*`: L0 ядро, контракты runtime/API.
- `detm_app/*`: orchestration, UI, transport, subscribers.
- `docs/rus/*`: канон документации.
- `docs/eng/*`: синхронизированный перевод.

## Запуск (минимум)

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python main.py --mode shell --steps 200 --size 128
```

## Артефакты наблюдения

- `trace.jsonl`
- `metrics.csv`
- `summary.json`
- `final_state.msgpack`

## Как читать дальше

1. `docs/rus/00_overview/README.md`
2. `docs/rus/10_model/model_core.md`
3. `docs/rus/20_mechanisms/*`
4. `docs/rus/50_experiments/*`
5. `docs/rus/ROADMAP.md`

