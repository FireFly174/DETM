# DETM — Discrete Entropy-Time Model

DETM — исследовательская дискретная модель динамики на решётке,
предназначенная для изучения возникновения устойчивых локализованных структур
(инвариантов) из строго локальных правил взаимодействия.

Проект фокусируется на механизмах коарсинга, асинхронности и внутреннего времени,
а не на априорном задании объектов или глобальных законов.

---

## Связь с DAGM (обобщение на граф)

Помимо решёточной реализации (DETM), в проекте фиксируется более абстрактная формулировка
**DAGM (Discrete Asynchronous Graph Model)**: дискретная асинхронная динамика на графе
с ограниченными потоками, где решётка является частным случаем графа.

- Каноническое описание DAGM: `docs/rus/10_model/dagm_core.md`
- Карта покрытия исходных заметок канонической документацией: `docs/rus/90_notes/source_materials.md` (сырьё хранится локально и не трекается git)

---

## Ключевая идея

Из простых локальных правил переноса и подавления может возникать:
- устойчивая объектоподобная динамика,
- многоуровневая структура,
- ограниченная пропускная способность уровня,
- фазовая согласованность без глобальной синхронизации.

Модель исследует **устойчивость как первичную наблюдаемую величину**.

---

## Что это НЕ

DETM:
- не является физической теорией;
- не описывает реальную Вселенную или фундаментальные силы;
- не моделирует сознание или интеллект;
- не утверждает сверхсветовой перенос или нарушение причинности.

Любые аналогии с физикой, биологией или когнитивными системами
рассматриваются только как внешние интерпретации.

---

## Структура проекта

- `docs/` — каноническая документация проекта  
  - `10_model` — формальная спецификация модели  
  - `20_mechanisms` — механизмы эмерджентной динамики  
  - `40_hypotheses` (RU) / `30_hypotheses` (EN) — проверяемые гипотезы  
  - `50_experiments` (RU) / `40_experiments` (EN) — экспериментальные протоколы  
  - `60_limits` (RU) / `50_limits` (EN) — ограничения и границы интерпретаций  
  - `90_notes` — архив идей и черновиков  

- `detm/` — реализация L0 (ядро + runtime-контракт)  
  - `detm/runtime/` — типизированный L0 API (`reset/step/digest/serialize`)
  - `detm/integrations/` — адаптеры для оркестраторов (ACGS/ComfyUI): `DETMRuntimeBridge`, `ACGSDetmBackend`
- `experiments/` — экспериментальные сценарии  
- `runs/`, `data/` — результаты запусков (обычно игнорируются git)

## Форматы данных и совместимость

Новые сценарии в `experiments/` пишут самоописательные артефакты (`metrics.csv`,
`final_state.npz`, `summary.json/catalog.json`) и используются как канонический
формат результатов. Скрипты из `legacy/export_*` и `legacy/bundle_*` поддерживаются
только для ручного разбора старых прогонов и не конвертируются в новый формат;
подробности — в `docs/rus/50_experiments/legacy_data_formats.md`.

## Документация (RU/EN)

- `docs/README.md`

---

## Конфигурация запуска (1 файл)

По умолчанию `python main.py` использует локальный файл `config.example.py` в корне репозитория:
- если файла нет, он автоматически копируется из `detm/presets/config.default.py`
- локальный `config.example.py` **не должен** трекаться git (он уже добавлен в `.gitignore`)
- без аргументов запускается napari interactive mode (`--interactive`)

Файл `config.example.py` — это Python-словарь `CONFIG` с секциями:
- runtime (поля `DETMConfig`): `backend/device/width/height/boundary/initial_noise/dynamics(a,b,g,k,t=alpha,beta,gamma,kappa,lambda_t)`
- `ui`: дефолты для UI (`UiRunSettings`)
- `runner`: дефолты для headless CLI (`detm_app.runner.headless`; `detm.cli` оставлен как deprecated facade)

Также можно передать свой конфиг:
- UI (napari): `python main.py napari --config config.local.py`
- UI (napari interactive controls, in-process): `python main.py napari --interactive --config config.local.py`
  - внутри dock есть режимы `interactive` и `batch` (пакетные прогоны + лог)
- Headless/batch: `python main.py --config config.local.py --batch 10`
- Composable shell roles: `python main.py shell --controller local --runner headless --viewer napari -- --seed 7 --steps 200 --fabric-handshake`

Справка по запуску:
- `python main.py --help` — только launcher-level режимы запуска
- `python main.py headless --help` — полный список headless параметров (включая расширенные внутренние knobs)

## Статус

Проект находится в активной исследовательской стадии.
Документация фиксирует текущее каноническое состояние модели.

Развитие проекта предполагает:
- воспроизводимые эксперименты,
- проверку гипотез,
- уточнение границ применимости.

---

## Лицензия и вклад

Проект распространяется под лицензией MIT.

- Лицензия: `LICENSE`
- Как вносить вклад: `CONTRIBUTING.md`
- Кодекс поведения: `CODE_OF_CONDUCT.md`
- Правила security-репортов: `SECURITY.md`
- Поддержка и каналы связи: `SUPPORT.md`
- Чеклист публичного релиза: `PUBLIC_RELEASE_CHECKLIST.md`

