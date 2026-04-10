# DETM: One Pager (RU)

## Что это

DETM (Discrete Entropy-Time Model) — исследовательский runtime для дискретной динамики на решётке.
Фокус проекта — устойчивые локальные структуры, коарсинг, асинхронность и внутреннее время, возникающие из локальных правил переноса и подавления.

## Что это не

- не физическая теория;
- не готовая AGI-система;
- не доказательство универсальных законов.

Это инженерная и исследовательская платформа для воспроизводимых экспериментов по самоорганизации и multilevel readout.

## Канонические слои

- `detm/*`: library-core, L0 runtime и контракты API.
- `detm_app/*`: orchestration, UI, transport, subscribers, analytics read-model.
- `docs/rus/*`: каноническая документация и roadmap.
- `docs/eng/*`: производная translation layer.

## Текущий статус

- Проверенный локальный snapshot (2026-04-10): `python main.py --help`, `pytest -q -> 439 passed in 16.51s`
- Закрыты baseline-треки: fabric production baseline, phase-F code contour, bounded N-D migration
- Открытый фокус: `G-RND-01`, `MSC-02`, public packaging (`PUB-01..03`), residual P1 structural debt
- Текущее runtime `coarsening` — это invariant/coarse-time stream layer; полноценный объектный `L0 -> L1` coarsener остаётся исследовательским треком

## Минимальный запуск

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install -e .
python main.py headless --seed 7 --steps 64 --batch 1 --out runs/out/quickstart --no-viz
```

UI-путь:

```powershell
python main.py napari --interactive
```

## Минимальные артефакты запуска

- `runs/out/quickstart/catalog.json`
- `runs/out/quickstart/seed_0000/config.json`
- `runs/out/quickstart/seed_0000/digest.json`
- `runs/out/quickstart/seed_0000/state.msgpack`
- `runs/out/quickstart/seed_0000/trace.jsonl`

## Куда читать дальше

1. `README.md`
2. `docs/rus/00_overview/README.md`
3. `docs/rus/10_model/model_core.md`
4. `docs/rus/ROADMAP_HUMAN.md`
5. `docs/rus/ROADMAP.md`
