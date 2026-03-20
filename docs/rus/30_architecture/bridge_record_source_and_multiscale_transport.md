# BridgeRecordSource и multiscale transport

Статус: RFC / следующий этап после `MSC-01`  
Обновлено: 2026-03-20

Связанные документы:
- `docs/rus/ROADMAP.md`
- `docs/rus/ROADMAP_HUMAN.md`
- `docs/rus/integration_contract.md`

## Зачем нужен этот RFC

`MSC-01` закрыл только bounded observe-only baseline:
- `multiscale_catalog` появился в `DETMConfig`;
- `pattern_memory` получил local ring buffer и `BridgeRecord`-shaped scaffold;
- runtime начал писать derived artifacts `multiscale_candidates.jsonl`, `scale_tension.jsonl`, `operator_catalog_hits.jsonl`;
- analytics ingest научился их индексировать.

Но это ещё не межуровневый execution bridge.

В текущем baseline отсутствуют:
- hot transport для runtime lookup;
- полные forward/reverse bodies траекторий;
- verification history и confidence calibration;
- источник истины для bridge-record bodies;
- формальный путь `observe -> verify -> activate -> retire`.

Этот RFC фиксирует следующий bounded шаг: как превратить observe-only multiscale слой в архитектурно честный bridge-contour, не подменяя канон `DETMState` и не объявляя premature `jump` semantics готовым production path.

## Ключевая идея

Межуровневая сущность должна быть не просто паттерном и не просто particle-like объектом.

Базовой единицей следующего этапа считается:

`BridgeRecordSource = полное описание воспроизводимого класса локальной траектории`

а в runtime hot-layer используется:

`BridgeRecord = исполнимая горячая проекция этого класса`

То есть:
- `BridgeRecordSource` хранит знание;
- `BridgeRecord` хранит действие;
- Redis нужен как доставка и hot index;
- trajectory store нужен как долговременная память полных forward/reverse bodies.

## Что именно должно храниться

### 1. Runtime grid memory

Это канонический слой текущего исполнения:
- текущий `DETMState`;
- короткое окно последних `K` snapshots активного уровня;
- локальные derived summaries для detect/observe path.

Этот слой остаётся owned runtime/session.

Он не должен:
- быть вынесен в Redis как source-of-truth;
- заменяться trajectory store DB;
- зависеть от availability Redis для корректного завершения run.

### 2. Redis bridge index

Redis нужен как hot transport и lookup-layer.

Он хранит:
- compact bridge records;
- hotness / usage / confidence;
- validity envelope;
- быстрые candidate queues (`coarsen`, `refine`, `attractor`);
- указатели на полные bodies в trajectory store DB.

Redis не хранит:
- dense grids;
- полные trajectories как архив;
- canonical `DETMState`;
- весь history экспериментов.

### 3. Trajectory store DB

Trajectory store DB хранит полные bodies и provenance:
- full micro-trajectories;
- compressed trajectories;
- verification history;
- equivalence classes;
- canonical representatives;
- serialized bridge-record sources.

На этом этапе не фиксируется одна конкретная СУБД как финальная архитектура.

Требование только такое:
- должен существовать durable source для full forward/reverse bodies;
- Redis должен держать только hot projection с указателями;
- local-first profile должен быть возможен.

Практически это допускает staged path:
- v1 local-first: SQLite + file-backed bodies / artifact refs;
- v2 shared profile: Postgres + object/file store;
- v3 distributed profile: отдельный trajectory service при реальной необходимости.

## Термины и роли

### BridgeRecordSource

Полное долговременное описание межуровневого оператора.

Минимальные поля:
- `source_id`
- `schema_version`
- `level_src`
- `level_dst`
- `window_geometry`
- `window_signature`
- `interface_signature`
- `horizon_k`
- `invariants_preserved`
- `forward_body_ref`
- `reverse_body_ref`
- `validity_envelope`
- `verification_summary`
- `provenance`
- `status`

Семантика:
- это не runtime cache;
- это долговременная запись класса траекторий;
- она должна быть достаточной для восстановления full body и повторной верификации.

### BridgeRecord

Горячая исполнимая проекция `BridgeRecordSource`.

Минимальные поля:
- `record_id`
- `source_id`
- `level`
- `window_signature`
- `interface_signature`
- `horizon_k`
- `forward_descriptor`
- `reverse_descriptor_short`
- `validity_envelope`
- `error_bound`
- `confidence`
- `usage_count`
- `last_verified_tick`
- `db_refs`

Семантика:
- это hot runtime object;
- он должен быть дешёвым для lookup;
- он не обязан содержать полный body;
- он обязан ссылаться на `BridgeRecordSource`.

### Forward body

Полное описание того, как локальная траектория нижнего уровня сворачивается в макропереход.

Это не обязательно список всех raw snapshots, но должно быть достаточно для:
- offline verification;
- повторного построения expected macro-step;
- оценки error и applicability.

### Reverse body

Полное описание того, как макропереход может быть развёрнут назад в допустимую микродинамику.

Важно:
- reverse не обязан быть точным inverse;
- reverse должен задавать допустимую refine/reconstruction semantics;
- один macro-step может иметь несколько допустимых reverse representatives.

## Контракт между уровнями

Следующий этап не должен трактовать `Ln+1` как “просто более крупную сетку”.

Правильная семантика:
- `Ln` считает детальную динамику;
- `BridgeRecordSource` фиксирует воспроизводимые классы локальной эволюции;
- `BridgeRecord` даёт runtime право быстро использовать уже верифицированный межуровневый оператор;
- `Ln+1` возникает как словарь допустимых макропереходов, а не как декоративная надстройка.

Это означает, что bridge-contract должен быть двусторонним:
- `ForwardCompress`
- `ReverseRefine`
- `ValidityEnvelope`

Без reverse/refine semantics нет честного межуровневого bridge; есть только jump-cache.

## Предлагаемый lifecycle

### Stage A — Observe

Источник: уже реализованный `MSC-01`.

Runtime:
- сканирует локальные окна;
- считает `window_signature`, `interface_signature`, temporal stability и transition stats;
- пишет candidates/readout artifacts;
- ничего не ускоряет и ничего не подменяет.

### Stage B — Persist

Новый следующий шаг.

Для устойчивых классов траекторий строится `BridgeRecordSource`:
- формируется `source_id`;
- сохраняются forward/reverse bodies;
- фиксируются invariants и validity envelope;
- запись попадает в trajectory store DB.

### Stage C — Activate

После накопления verification evidence создаётся hot `BridgeRecord`:
- compact descriptor;
- confidence/error/hotness;
- refs на full bodies;
- запись публикуется/обновляется в Redis.

### Stage D — Hint

Runtime начинает читать Redis как suggestion-layer:
- `operator_reuse_candidate`
- `coarsen_candidate`
- `refine_candidate`
- `attractor_candidate`

Но canonical `step()` ещё не подменяется.

### Stage E — Guarded Jump

Только после отдельного acceptance gate.

Runtime может использовать `jump(window, k)` лишь если:
- `BridgeRecord` свежий;
- interface sufficiently similar;
- error bound ниже порога;
- рядом нет unstable boundary;
- post-check обязателен;
- есть fallback на честный `step`.

## Что должно считаться инвариантами bridge-контракта

Следующий этап обязан явно различать:

### Что сохраняется

Минимальный список:
- energy-level summaries;
- interface flux / boundary summaries;
- topological class of region, если он используется;
- signature-level quality metrics;
- допустимые limits на drift/error.

### Что допускается терять

Минимальный список:
- мелкие флуктуации;
- перестановки эквивалентных микросостояний;
- шум, который не влияет на acceptance-инварианты;
- detail, не нужный для последующего refine.

Без этой границы любая будущая `jump`-семантика будет либо нечестной, либо слишком дорогой.

## Redis keyspace (предварительно)

Ключи не финализированы, но роли должны быть такими:

- `bridge:hot:{level}:{window_sig}:{interface_sig}:{horizon}`
  горячий `BridgeRecord`
- `bridge:source:{source_id}`
  compact metadata mirror для быстрых lookups
- `cand:coarsen:{level}`
  sorted-set или аналог для coarsen candidates
- `cand:refine:{level}`
  sorted-set или аналог для refine candidates
- `node:{level_plus_1}:{node_id}`
  активные macro candidates / attractor-like carriers

Ограничения:
- никакого full-grid dump;
- никакого длинного archive history;
- никакого хранения secret-bearing DSN в экспортируемых артефактах;
- hot-layer обязан быть reconstructible из trajectory store DB.

## Trajectory store: минимальная сущностная модель

Следующий этап должен различать минимум пять сущностей:

### RawTrajectory

Честная низкоуровневая траектория или её достаточное представление.

### CompressedTrajectory

Свёрнутое представление той же динамики на более высоком уровне описания.

### BridgeRecordSource

Связующее полное описание между `RawTrajectory` и `CompressedTrajectory`.

### VerificationRun

История проверок bridge semantics:
- где сработало;
- где не сработало;
- при каких interface conditions;
- какой drift/error был получен.

### EquivalenceClass / CanonicalRepresentative

Класс похожих траекторий и его канонический представитель.

Без этого Redis hot-layer быстро выродится в неуправляемый cache ad hoc записей.

## Non-goals этого RFC

Этот RFC специально не делает следующее:
- не включает live runtime `jump`;
- не включает policy-driven `hint` execution как уже готовый contract;
- не объявляет particle/macronode semantics завершённой;
- не переводит `DETMState` в Redis;
- не меняет artifact-first канон;
- не навязывает одну final DB technology;
- не обещает exact replay как обязательный reverse mode.

## Минимальный следующий deliverable

Следующий bounded engineering step после этого RFC должен быть не `jump`, а doc+schema+storage baseline:

1. Формализовать `BridgeRecordSource` schema.
2. Ввести trajectory store contract и refs.
3. Добавить persist-path из observe-only candidates в durable source.
4. Добавить Redis hot mirror для compact `BridgeRecord`.
5. Добавить verification artifacts/readout, не включая runtime substitution.

То есть сначала:

`observe -> persist -> verify -> activate`

и только после этого:

`hint -> guarded jump`

## Acceptance question

Главный контрольный вопрос для следующего этапа:

> Добавляем ли мы честный межуровневый контракт с двусторонней semantics и верификацией,
> или просто строим быстрый cache, который притворяется новой архитектурой?
