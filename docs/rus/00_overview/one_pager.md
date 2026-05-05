# DETM: One Pager (RU)

## Что это

DETM (Discrete Entropy-Time Model) - исследовательский runtime для дискретной
динамики на решетке. Проект изучает, при каких локальных правилах переноса и
подавления возникают устойчивые локализованные структуры, коарсинг,
асинхронность и внутреннее время.

Практически это reproducible research workspace: код, сценарии запусков,
артефакты и документация связаны так, чтобы результат можно было повторить и
проверить по файлам, а не только по описанию.

## Что это не

- не физическая теория;
- не модель реальной Вселенной;
- не AGI-система;
- не доказательство универсальных законов;
- не финальная архитектура многоуровневого coarsening.

Внешние аналогии допустимы только как интерпретации. Канон проекта - локальная
динамика, артефакты запуска, trace/readout и явно зафиксированные ограничения.

## Как устроены слои

- `detm/*` - library-core и runtime contracts.
- `detm_app/*` - orchestration, UI, transport, subscribers, analytics read-model.
- `experiments/*` - воспроизводимые сценарии и публичные preset/config пакеты.
- `docs/rus/*` - canonical documentation и roadmap source-of-truth.
- `docs/eng/*` - производная English translation layer.
- `docs/media/*` - curated public preview/readout artifacts.

Внешний доступ к состоянию остается artifact-first: `System Trace`, `Watch Trace`,
`OuterFields`, `trace_ref`, summary/readout files. SQLite analytics read-model -
производный слой поверх raw artifacts, не замена source-of-truth.

## Текущий статус

- Verified baseline: `python main.py --help`, `pytest -> 439 passed`.
- Закрыты: fabric production baseline, phase-F code contour, bounded N-D migration.
- Закрыт public packaging baseline: `PUB-01` media readouts, `PUB-02` visual presets, `PUB-03` one-page overview.
- Открытый фокус: `G-RND-01`, `MSC-02`, follow-up к analytics/outerfields retention, residual P1 structural debt.
- Transition layers нельзя трактовать как final architecture: current multiscale catalog, analytics read-model, visual presets и `channel_tunnel` preset остаются bounded readout/packaging layers.

## Быстрый запуск

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install -e .
python main.py headless --seed 7 --steps 64 --batch 1 --out runs/out/quickstart --no-viz
```

Ожидаемые артефакты:

- `runs/out/quickstart/catalog.json`
- `runs/out/quickstart/seed_0000/config.json`
- `runs/out/quickstart/seed_0000/digest.json`
- `runs/out/quickstart/seed_0000/state.msgpack`
- `runs/out/quickstart/seed_0000/trace.jsonl`

Интерактивный UI:

```powershell
python main.py napari --interactive
```

## Публичные readout и presets

Curated media:

- `docs/media/png/beta_kappa_phase_map.png`
- `docs/media/png/beta_viscosity_readout.png`
- `docs/media/png/kappa_viscosity_readout.png`

Регенерация:

```powershell
python -m experiments.11_beta_kappa_phase_map.analyze
python -m experiments.pub01_media_assets
```

Visual presets:

- `experiments/12_public_visual_presets/classic_coarsing.json`
- `experiments/12_public_visual_presets/stable_object.json`
- `experiments/12_public_visual_presets/channel_tunnel.json`

Пример запуска:

```powershell
python -m experiments.marker_protocol --config experiments/12_public_visual_presets/stable_object.json
```

## Куда смотреть дальше

1. `README.md` - основной вход в репозиторий.
2. `docs/rus/README.md` - canonical RU docs index.
3. `docs/rus/ROADMAP_HUMAN.md` - краткая дорожная карта.
4. `docs/rus/ROADMAP.md` - engineering source-of-truth по статусам и зависимостям.
5. `experiments/README.md` - список воспроизводимых сценариев.
6. `docs/media/README.md` - публичные preview/readout artifacts.

