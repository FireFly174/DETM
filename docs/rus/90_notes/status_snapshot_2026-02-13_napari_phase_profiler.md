# Status Snapshot: napari startup phase-profiler (2026-02-13)

## Что завершено

- В `main.py napari` добавлен phase-profiler старта по фазам:
  - `producer_wait_s`
  - `napari_qt_import_s`
  - `viewer_create_s`
  - `first_frame_s` (+ `first_frame_status`)
- Профиль старта выводится в stdout как JSON-строка (`[napari-phase-profile] {...}`).
- Добавлен экспорт профиля в файл: `--phase-profile-json <path>`.
- Добавлен non-interactive режим `--startup-only`:
  - выполняет startup-профилирование;
  - завершает запуск до входа в `napari.run()`;
  - удобен для baseline/CI/автоматизации.

## Где реализовано

- `detm_app/ui/napari/lab.py`
  - сбор `producer_wait_s`;
  - CLI-флаги `--phase-profile-json`, `--startup-only`;
  - запись JSON baseline.
- `detm_app/ui/napari/subscriber.py`
  - заполнение `napari_qt_import_s`, `viewer_create_s`, `first_frame_s`, `first_frame_status`;
  - режим `startup_only`.
- `tests/test_napari_lab_launcher.py`
  - покрытие прокидывания `startup_profile/startup_only`;
  - проверка записи JSON профиля.

## Проверки

- `pytest -q tests/test_napari_lab_launcher.py tests/test_napari_subscriber_path.py` -> `24 passed`
- `pytest -q tests/test_main_entrypoint_routing.py tests/test_shell_orchestrate.py tests/test_entrypoints_use_detm_app.py` -> `15 passed`

## Baseline (локальный запуск 2026-02-13)

Команда:

`python main.py napari --startup-only --phase-profile-json runs/out/napari_startup_phase_profile_2026-02-13.json -- --seed 7 --steps 120 --steps-mode total`

Результат:

- `producer_wait_s = 0.37839`
- `napari_qt_import_s = 0.137447`
- `viewer_create_s = 4.848822`
- `first_frame_s = 1.204151`
- `first_frame_status = rendered`

Артефакт:

- `runs/out/napari_startup_phase_profile_2026-02-13.json`

## Текущее узкое место

- Главная задержка старта остаётся в `viewer_create_s` (`napari.Viewer(...)`): ~`4.85s` на этом окружении.

## Следующий шаг

- Разложить `viewer_create_s` на подфазы (Qt bootstrap, plugin discovery, viewer init), снять cold/warm baseline и выбрать пакет оптимизаций.
