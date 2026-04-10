# `90_notes` — curated support layer

`docs/rus/90_notes/` больше не используется как общий архив для всего подряд.
Это tracked-слой для актуальных supporting/governance notes, на которые допустимо ссылаться из канонических RU-docs.

## Что хранится здесь

- governance и operational notes для docs/agent workspace;
- still-referenced conceptual notes, которые реально поддерживают `10_model`, `20_mechanisms`, `30_architecture`, `40_hypotheses`;
- supporting materials, которые ещё нужны как рабочий bridge между каноном и исследовательским слоем.

## Что сюда не кладём

- status snapshots, recovery notes, backlog/audit/rewrite материалы;
- chat-like synthesis и временные сводки;
- docs-ops generated artifacts (`docs_memory_*`, `docs_non_md_inventory_*`, `runtime_oop_hotspots_*` и аналогичные выгрузки).

## Куда уходит архив и служебный слой

- локальный архив исторических заметок: `docs/source/archive/90_notes/`
- локальные docs-ops generated artifacts: `docs/source/generated/docs_ops/`

`docs/source/**` рассматривается как local raw/archive/generated layer и игнорируется git.
Туда можно уносить дезориентирующий материал без засорения канонической навигации.

## Правило ссылок

- из канонических docs ссылаться только на актуальные notes в `docs/rus/90_notes/`;
- historical archive допускается упоминать только как archival/historical reference, но не как текущий source-of-truth;
- новые служебные выгрузки не коммитить обратно в `90_notes`.
