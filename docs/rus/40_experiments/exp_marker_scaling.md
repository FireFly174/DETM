# Протоколы `marker_protocol` и `scaling_protocol`

Новые сценарии в каталоге `experiments/` переносят логику из legacy-скриптов
`analyze_grid_timeseries.py` и `bundle_timeseries.py` на API `detm.core.entropy`.
Сохраняется акцент на компактных метриках и воспроизводимости запуска.

## Общие метрики

- глобальные инварианты: `mean/min/max/var` энергии, `mean` энтропии и внутреннего времени;
- доминирующая частота траектории `energy_mean` (rFFT без DC, как в legacy анализе);
- снепшот финального состояния (`final_state.npz`) для последующей визуализации.

Все метрики пишутся в `metrics.csv` внутри папок запусков и агрегируются в
`summary.csv`/`catalog.json`.

## Marker protocol

Цель — проверить устойчивость локального «маркера» (пятно повышенной энергии).
Дополнительно логируются средние энергии **внутри** маски и **снаружи**.

### Конфиг (JSON/YAML)

```json
{
  "size": 24,
  "steps": 240,
  "seeds": [1, 2, 3],
  "noise": 0.08,
  "boundary": "periodic",
  "out": "runs/marker_protocol",
  "dynamics": {"equilibrium_energy": 0.55, "kappa": 0.08, "alpha": 0.9},
  "marker": {"radius": 3, "energy": 0.95}
}
```

### Команда

```bash
python experiments/marker_protocol.py --config cfg/marker.json
```

CLI-параметры перекрывают конфиг (например, `--marker-radius 4` или
`--no-energy-bounds`).

## Scaling protocol

Цель — снять базовые метрики при разных размерах решётки и seeds.

### Конфиг (JSON/YAML)

```json
{
  "sizes": [12, 18, 24, 30],
  "seeds": [1, 2],
  "steps": 200,
  "noise": 0.08,
  "boundary": "periodic",
  "out": "runs/scaling_protocol",
  "dynamics": {"equilibrium_energy": 0.52, "kappa": 0.07}
}
```

### Команда

```bash
python experiments/scaling_protocol.py --config cfg/scaling.json
```

Или без файлов: `python experiments/scaling_protocol.py --sizes 16 32 --steps 120 --seeds 5 6`.

## Что сохраняется

- `metrics.csv` — пометки всех шагов (можно использовать вместо legacy `*_timeseries.py`);
- `final_state.npz` — энергетика, энтропия, внутреннее время (и маска маркера);
- `summary.json` внутри каждого запуска и общий `catalog.json` для серии.

Формат выходов подобран так, чтобы их можно было собрать/сжать аналогично
legacy `bundle_timeseries.py` или анализировать частотные карты как
`analyze_grid_timeseries.py`.
