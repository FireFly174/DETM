# Status Snapshot: fabric + napari (2026-02-12)

## Что завершено

- Runtime `fabric` полностью консолидирован в `detm/runtime/fabric/...`.
- Legacy namespace `detm/runtime/fabric_*` удалён (и папки, и shim-модули).
- Внутренние импорты переведены на `detm.runtime.fabric`.
- Для napari-пути убран лишний import overhead:
  - `detm_app/__init__.py` переведён на lazy exports;
  - `detm_app/ui/napari/subscriber.py` использует lazy import `detm.runtime.api`.

## Проверки

- `pytest -q`: `243 passed, 1 skipped`.
- Замеры импортов:
  - `import detm_app.ui.napari.lab`: `~0.236s -> ~0.096s`
  - `import detm_app.ui.napari.subscriber`: `~0.250s -> ~0.090s`

## Текущее узкое место

- Основная задержка старта napari остаётся в инициализации viewer/Qt:
  - `napari.Viewer(...)`: около `~3.3s` на текущем окружении.

## Где остановились

- Следующий шаг не реализован: phase-profiler для `main.py napari` с таймингами фаз:
  - `producer endpoint wait`
  - `napari/qt import`
  - `viewer create`
  - `first frame render`
