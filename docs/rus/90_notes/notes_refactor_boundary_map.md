# Note1-5 Refactor Boundary Map

Статус: рабочая карта для чтения notes через границу `docs + code`.  
Документ не меняет канон DETM и не заменяет `limits.md`, `model_core.md`, `L0_foundations.md` или roadmap.

Цель этой карты:
- зафиксировать, какие смыслы из `Note1-5` допустимо поднимать в канон, гипотезы, архитектурные RFC или только в интерпретационный слой;
- зафиксировать, какие рефакторинги из этих notes разрешены, запрещены или требуют сначала doc-first контракта.

Короткая формула:
- `notes` являются генератором языка и направлений;
- канон остаётся в `10_model/*`, `60_limits/*`, `30_architecture/*`, `ROADMAP*`;
- рефакторинг допустим только тогда, когда статус идеи понятен и не нарушает `single-writer`, `artifact-first`, `coarsen <-> refine`, локальность и разделение `detm` / `detm_app`.

## Канонические якоря

Любая трактовка ниже должна читаться через эти документы:
- `docs/rus/10_model/model_core.md`
- `docs/rus/10_model/L0_foundations.md`
- `docs/rus/60_limits/limits.md`
- `docs/rus/ROADMAP_HUMAN.md`
- `docs/rus/00_overview/architecture.md`

---

## Refactor Meaning

В этой карте используются три класса рефакторинга.

### Structural refactor

Изменяет устройство кода без изменения канона:
- декомпозиция модулей;
- выравнивание границ слоёв;
- перенос orchestration/UI/transport/storage;
- cleanup import direction и package structure.

Structural refactor допустим, если не меняет базовую механику `step/state/coarsen/refine` и не подменяет source-of-truth.

### Semantic refactor

Изменяет то, как уже существующий канон выражается в коде или документах:
- уточнение терминов;
- перенос формулировок в более жёсткий контракт;
- улучшение readouts, metrics и diagnostics;
- выравнивание runtime/docs без смены инвариантов.

Semantic refactor допустим, если не меняет базовые L0/L1 инварианты и не превращает гипотезу в канон.

### Model refactor

Изменяет саму механику:
- `step`;
- базовое состояние;
- причинность;
- `coarsen/refine`;
- межуровневую законность;
- interpretation of transport/time/packet semantics.

Model refactor требует:
- отдельного doc-first контракта или RFC;
- явного набора falsification conditions;
- bounded implementation path;
- проверки на совместимость с `limits.md` и текущим каноном.

Практический вывод:
- большинство идей из `Note1-5` пока тянут либо на `interpretation`, либо на `model refactor`;
- они не должны автоматически превращаться в обычный structural cleanup.

---

## Note 1

Источник: `docs/rus/note1.md`

### Core idea

`note1` — это источник физической интуиции и опасных аналогий:
- энергия, кинетика, потенциал, граница взаимодействия;
- попытка читать DETM через язык физики высокого уровня;
- поиски L2-языка поверх канона, а не внутри него.

### Status

`interpretation-only`

### Code impact

Прямого входа в runtime-рефакторинг нет.

Допустимо:
- использовать как язык для гипотез и explanatory notes;
- использовать как L2-интерпретацию поверх уже существующего канона;
- использовать как источник словаря для docs, если это не подменяет `model_core.md`.

Недопустимо:
- переписывать `step`, `state`, `energy`, `time`, `coarsen/refine` по мотивам `note1`;
- объявлять физические аналогии частью ядра без отдельной формализации и falsification.

### Doc impact

Подходит только для:
- интерпретационных заметок;
- L2-языка;
- аккуратных bridges в hypothesis-level docs.

Не подходит для:
- канона;
- архитектурных RFC;
- project constitution.

### Refactor limit

Прямой рефакторинг ядра по мотивам `note1` запрещён без:
- отдельной формализации;
- проверки на совместимость с `limits.md`;
- явного falsification plan.

---

## Note 2

Источник: `docs/rus/note2.md`

### Core idea

`note2` задаёт исследовательскую рамку:
- lawful folding;
- objecthood-as-crystallization;
- observer/tracking;
- long-horizon runtime как настоящий frontier;
- отказ от “ещё одной красивой общей теории” в пользу устойчивой многослойной траектории.

### Status

`hypothesis-safe`

### Code impact

Это сильный вход в:
- readout;
- metrics;
- diagnostics;
- candidate-selection;
- multiscale validation;
- tracking/identity layer.

Допустимо:
- улучшать docs гипотез;
- усиливать артефакты наблюдаемости;
- добавлять object candidate detectors, tracking, diagnostic metrics, read-model summaries;
- строить bounded validation layers поверх существующего runtime.

Недопустимо:
- напрямую переписывать ядро под “новую физику lawful folding”;
- объявлять кандидатов на объектность частью канона без traceable criteria.

### Doc impact

Подходит для:
- гипотез;
- readout contracts;
- multiscale/observer/identity RFC;
- диагностических документов.

### Refactor limit

`note2` можно использовать как justification для:
- semantic refactor в docs/readout;
- structural refactor вокруг diagnostics/analytics/subscribers.

`note2` нельзя использовать как justification для model rewrite `detm/core` без отдельного RFC.

---

## Note 3

Источник: `docs/rus/Note3.md`

### Core idea

`Note3` — мост между:
- режимами среды (`kappa`);
- объектом;
- границей;
- локальным переносом;
- правом на смену масштаба наблюдения.

В нём появляется более жёсткая тройка:
- центр состояния;
- граница как интерфейс;
- энергия/поток на границе.

### Status

`hypothesis-safe`

### Code impact

Допустимо:
- усиливать object/boundary metrics;
- уточнять lawfulness criteria for coarsening;
- добавлять readouts по границе, режимам и candidate interfaces;
- развивать experiments и diagnostics вокруг `kappa`, mask/boundary, object candidates.

Недопустимо:
- объявить `kappa` новой фундаментальной осью канона;
- вводить новый базовый state primitive без RFC;
- молча менять L0 runtime semantics под новую интерпретацию объекта и границы.

### Doc impact

Подходит для:
- hypothesis cards;
- docs уровня `20_mechanisms` и `40_hypotheses`;
- object/boundary transfer framing;
- объяснения, почему смена режима наблюдения может быть законной.

### Refactor limit

`Note3` разрешает:
- semantic refactor в readout/hypothesis docs;
- bounded diagnostics/experiment work.

`Note3` не разрешает:
- прямой model refactor ядра без промежуточного doc-first контракта.

---

## Note 4

Источник: `docs/rus/Note4.md`

### Core idea

`Note4` — фактическая конституция проекта:
- `detm` считает;
- `detm_app` организует;
- подписчики наблюдают;
- артефакты являются правдой.

Это не свободная интерпретация, а набор проектных тормозов:
- `detm` vs `detm_app`;
- `single-writer`;
- `artifact-first`;
- `coarsen <-> refine`;
- anti-magic;
- anti-interpretation drift.

### Status

`refactor-driver`

### Code impact

Любой архитектурный рефакторинг обязан сначала пройти через ограничения `Note4`.

Разрешает:
- structural refactor границ слоёв;
- cleanup orchestration/UI/transport/storage;
- усиление source-of-truth discipline;
- усиление `detm` как ядра и `detm_app` как orchestration-layer.

Запрещает:
- перенос канона в UI, transport или analytics;
- live-state authority outside runtime;
- скрытые альтернативные физики в app-layer;
- разрыв пары `coarsen/refine`.

### Doc impact

`Note4` стоит читать как operational guardrail и reference document при:
- оценке PR;
- планировании рефакторинга;
- решении, куда класть новую идею;
- обсуждении границ `detm` / `detm_app`.

### Refactor limit

Если идея конфликтует с `Note4`, то:
- structural refactor запрещён;
- semantic refactor требует отдельного justification;
- model refactor требует сначала RFC и, вероятно, пересмотра ограничений выше уровня note-stack.

Практически `Note4` доминирует над остальными notes как guardrail.

---

## Note 5

Источник: `docs/rus/note5.md`

### Core idea

`note5` вводит свежую онтологию:
- `boundary -> packet -> fire/publish -> UDP/spike`;
- перевод элементарного обмена в событийную модель;
- reinterpretation of `step` как trigger-based fire-and-publish;
- связь с нейроноподобным спайковым интерфейсом.

### Status

`not-ready`

### Code impact

Сейчас это не канон и не прямое основание для runtime rewrite.

Разрешено:
- doc-first формализация как `L2 interpretation`;
- отдельная hypothesis card или RFC уровня `runtime alternative semantics`;
- bounded prototype в experimental или alternative runtime path;
- обсуждение impact на `entropy.step()` как исследовательского направления.

Не разрешено:
- прямой рефакторинг `entropy.step()` в каноническом runtime;
- молчаливое удаление текущей механики в пользу UDP/spike;
- объявление новой онтологии “просто лучшей интерпретацией” без falsification и compatibility check.

### Doc impact

Следующий корректный шаг для `note5` — не код, а документ:
- короткий `L2 interpretation` doc;
- или RFC по альтернативной семантике runtime;
- или bounded experiment protocol.

Только после этого можно обсуждать prototype path.

### Refactor limit

`note5` — это потенциальный `model refactor`, а не обычный refactor cleanup.

Без промежуточного документа считать прямое изменение `entropy.step()` преждевременным.

---

## Сводная таблица

| Note | Основной статус | Разрешено сейчас | Только после RFC / doc-first | Нельзя сейчас |
| --- | --- | --- | --- | --- |
| `note1` | `interpretation-only` | внешняя интерпретация, L2-язык, explanatory docs | формализация в отдельной hypothesis card | прямой рефакторинг ядра по физическим аналогиям |
| `note2` | `hypothesis-safe` | docs, diagnostics, tracking, metrics, candidate-selection, multiscale validation | model-level lawful folding contracts | переписывать ядро под “новую физику” |
| `Note3` | `hypothesis-safe` | object/boundary metrics, readouts, experiments, lawfulness criteria | новые state/interface primitives | менять L0 runtime semantics без RFC |
| `Note4` | `refactor-driver` | structural cleanup, boundary enforcement, source-of-truth discipline | пересмотр конституционных ограничений | всё, что ломает `single-writer`, `artifact-first`, `detm` vs `detm_app` |
| `note5` | `not-ready` | doc-first формализация, bounded prototype path, experiment design | alternative runtime semantics RFC | прямой rewrite `entropy.step()` в каноне |

---

## Decision Checklist

Перед любым новым модулем или рефакторингом проверять:
- усиливает ли это `detm` как ядро, а не размывает его;
- остаётся ли `detm_app` orchestration-only;
- не подменяет ли это raw artifacts как source-of-truth;
- не ломает ли это `single-writer`;
- не превращает ли гипотезу в канон без эксперимента;
- не вводит ли hidden nonlocality;
- не разрывает ли пару `coarsen/refine`;
- не использует ли `note5`-подобную онтологию как оправдание для немедленного model rewrite;
- не конфликтует ли это с `limits.md`, `model_core.md`, `L0_foundations.md`, `ROADMAP_HUMAN.md`.

---

## Короткий вывод

`Note1-5` не равны по статусу.

Если грубо:
- `note1` даёт язык;
- `note2` и `Note3` дают гипотезы и критерии наблюдаемости;
- `Note4` задаёт конституционные пределы;
- `note5` даёт сильный новый импульс, но пока только как `doc-first before code`.

Главный смысл для рефакторинга:
- structural cleanup допустим широко, если он проходит через `Note4`;
- semantic changes допустимы там, где они не меняют канон;
- model refactor по мотивам `Note1-5` почти везде требует сначала документ, затем bounded эксперимент, затем falsification.
