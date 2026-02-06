"""Default single-file config for local development.

This file is a template. `python main.py` (with no args) will copy it into the
repo root as `config.example.py` if missing, and will use that local file on
subsequent launches.
"""

# Можно также реализовать `get_config()` / `load_config()` и вернуть dict.
CONFIG = {
    "backend": "torch",  # torch | numpy  /// вычислительный бэкенд
    "device": "cuda",  # cuda | cpu | cuda:0  /// устройство исполнения
    # minimal | cpu_full  /// режим формирования observables (cpu_full разрешает тяжёлые CPU-анализы)
    "observables_mode": "minimal",
    "trace_boundary_flux": False,  # False | True  /// log Φ_boundary(t) proxies into trace.jsonl
    "width": 24,  # int > 0  /// ширина решётки
    "height": 24,  # int > 0  /// высота решётки
    "boundary": "periodic",  # periodic | open  /// условие границы
    "initial_noise": 0.08,  # float >= 0  /// шум начального E
    # a,b,k,g,t в UI: alpha,beta,kappa,gamma,lambda_t  /// параметры динамики
    "dynamics": {
        "equilibrium_energy": 0.5,  # float 0..1  /// базовый уровень энергии
        "alpha": 0.3,  # float >= 0  /// подавление переноса энтропией
        "beta": 0.8,  # float >= 0  /// вес локального отклонения
        "gamma": 0.1,  # float >= 0  /// вес отклонения соседей
        "kappa": 0.1,  # float >= 0  /// проводимость переноса
        "lambda_t": 1.0,  # float >= 0  /// влияние энтропии на время
        "activation_threshold": 1.0,  # float > 0  /// порог активации переноса
        "energy_bounds": (0.0, 1.0),  # (lo,hi) | None  /// ограничение энергии
    },
    "ui": {
        "seed": 1,  # int >= 0  /// seed для UI-сессии
        "ticks_per_step": 4,  # int > 0  /// L0-тиков на шаг UI
        "tick_interval_ms": 60,  # int >= 1  /// задержка между шагами
        # symbol | joystick_field | joystick_patch | source_sink | none  /// режим влияния
        "influence_mode": "symbol",
        "symbol_id": "pulse",  # list_symbols() | (none)  /// символ влияния
        "amplitude": 1.0,  # float  /// сила влияния
        "influence_duration_steps": 0,  # 0 | int > 0  /// длительность влияния
        "joy_dx": 0.0,  # float -1..1  /// наклон поля по X
        "joy_dy": 0.0,  # float -1..1  /// наклон поля по Y
        "patch_cx": 12,  # int 0..W-1  /// центр патча по X
        "patch_cy": 12,  # int 0..H-1  /// центр патча по Y
        "patch_radius": 6,  # int >= 0  /// радиус патча
        "source_x": 6,  # int 0..W-1  /// X источника энергии
        "source_y": 12,  # int 0..H-1  /// Y источника энергии
        "sink_x": 18,  # int 0..W-1  /// X стока энергии
        "sink_y": 12,  # int 0..H-1  /// Y стока энергии
        "source_value": 1.0,  # float 0..1  /// значение источника
        "sink_value": 0.0,  # float 0..1  /// значение стока
        "record_dir": "runs/out/ui_run",  # path | None  /// директория записи
        "record_fields": False,  # False | True  /// запись fields_hist.npz
        "invariant_streams": "",  # "" | "inv0=1/10,..."  /// инвариантные тики
        "viz_enabled": True,  # False | True  /// включить viz-демон
        "viz_transport": "embedded",  # embedded | tcp | none  /// транспорт визуализации
        "viz_host": "127.0.0.1",  # host  /// адрес viz-демона
        "viz_port": 0,  # 0 | int > 0  /// порт viz-демона
        "viz_connect": False,  # False | True  /// connect к внешнему daemon
        "viz_keep_open": False,  # False | True  /// не закрывать daemon
        "viz_every_steps": 1,  # int > 0  /// период отправки кадров
    },
    "runner": {
        "seed": 1,  # int >= 0  /// seed одиночного запуска
        "seed0": 0,  # int >= 0  /// старт seed для batch
        "steps": 4,  # int > 0  /// тиков на влияние
        # None | list[str] | "a,b"  /// список символов
        "symbols": None,
        "out": None,  # path | None  /// корень выходных данных
        "viz": False,  # False | True  /// включить viz в headless
        "viz_transport": "tcp",  # tcp | none  /// транспорт viz
        "viz_host": "127.0.0.1",  # host  /// адрес viz
        "viz_port": 0,  # 0 | int > 0  /// порт viz
        "viz_connect": False,  # False | True  /// connect к внешнему daemon
        "viz_keep_open": False,  # False | True  /// не закрывать daemon
        "viz_every_steps": 1,  # int > 0  /// период отправки кадров
        "record_fields": False,  # False | True  /// запись fields_hist.npz
        "fields_every_steps": 1,  # int > 0  /// период записи полей
        # None | list[str] | "inv0=1/10,..."  /// инвариантные потоки
        "invariant_streams": None,
    },
}
