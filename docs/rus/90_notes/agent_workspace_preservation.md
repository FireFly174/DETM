# DETM Agent Workspace Preservation

Статус: локальный operational runbook для Codex и других coding agents.

Цель: зафиксировать, какие части агентного окружения в DETM уже являются рабочей инфраструктурой и должны сохраняться при дальнейшей настройке репозитория.

Этот документ дополняет:
- `AGENTS.md`
- `docs/rus/90_notes/memory_playbook_detm.md`

Он не заменяет `.codex/PROMT.md`, roadmap или source-of-truth docs по самой архитектуре DETM.

## 1) Что считается уже построенной инфраструктурой

Считать штатными и сохраняемыми артефактами:

- repo-root policy: `AGENTS.md`
- prompt stack: `.codex/SYSTEM_PROMT_DETM_CREATIVE.md`, `.codex/PROMT.md`
- roadmap stack: `docs/rus/ROADMAP.md`, `docs/rus/ROADMAP_HUMAN.md`
- memory layer: `.aimemo/` и `docs/rus/90_notes/memory_playbook_detm.md`
- repo-local launcher layer: `_mcp_launchers/*`

Если агенту нужно улучшить рабочее окружение, улучшение должно быть additive и reviewable, а не через полную регенерацию этих файлов.

## 2) Что находится вне репозитория, но должно учитываться

DETM уже строился в окружении, где часть инфраструктуры живёт вне репозитория:

- глобальный Codex config: `C:\Users\FireFly74\.codex\config.toml`
- глобальная библиотека skills: `C:\Users\FireFly74\.codex\skills`
- central common policy: `D:\01 Projects\Agent\AGENTS.md`
- внешние MCP server roots и launch paths, на которые ссылаются `_mcp_launchers/*`

Вывод:

- не копировать глобальные skills в DETM;
- не пытаться «заново bootstrap-ить» репозиторий ради дублирования глобального конфига;
- repo-local docs должны описывать, как использовать уже существующую схему, а не заменять её.

## 3) Инструментальная логика для DETM

При работе в `D:\github\DETM` агент должен предпочитать следующую схему:

1. policy/bootstrap:
   - `AGENTS.md`
   - `.codex/PROMT.md` stack по локальному контракту
2. project memory:
   - `aimemo_detm_memory`
   - затем локальные canonical docs
3. repo operations:
   - `git_detm`
4. filesystem access:
   - `fast-filesystem` при доступности и корректном allow-list
   - fallback: `filesystem` и shell
5. local repair/debug:
   - `_mcp_launchers/*` использовать как reference layer для wiring/repair задач, а не как материал для автоперезаписи

Если часть инструментации временно недоступна, агент должен деградировать мягко:
- сначала fallback на другой доступный инструмент;
- затем на shell/manual verification;
- без переписывания всего bootstrap слоя.

## 4) Политика по skills

Skills считаются внешним capability-layer, а не частью DETM source tree.

Правила:

- использовать глобальные skills, когда задача им соответствует;
- не дублировать skill bodies в DETM;
- не создавать repo-local pseudo-bootstrap, который перетирает существующие `_mcp_launchers`, `AGENTS.md`;
- не использовать `bootstrap-repository` для DETM без отдельного ручного review, потому что в репозитории уже есть важные hand-crafted артефакты.

## 5) Что нельзя перетирать автоматически

Без явного запроса пользователя не регенерировать и не массово переписывать:

- `AGENTS.md`
- `_mcp_launchers/*`
- `.aimemo/*`
- `.codex/PROMT.md`
- `.codex/SYSTEM_PROMT_DETM_CREATIVE.md`
- `docs/rus/ROADMAP.md`
- `docs/rus/ROADMAP_HUMAN.md`

Если изменение нужно, оно должно быть:

- локальным;
- объяснимым;
- обратимым;
- совместимым с уже работающей схемой.

## 6) Worktree discipline

Для DETM worktree допустим как изолированный execution sandbox, но после merge/push он не должен оставаться «висящим» без причины.

Рекомендуемая логика:

1. проверить, что нужные изменения уже перенесены в основной workspace и запушены;
2. проверить, что основной `dev/main` чистый;
3. после этого удалить stale worktree;
4. локальную feature-ветку удалять только если она больше не нужна как reference.

Это cleanup-политика, а не часть архитектуры DETM.

## 7) Практический чеклист для нового агентного цикла

Перед существенной работой в DETM:

1. восстановить project memory (`aimemo_detm_memory`);
2. прочитать локальный `AGENTS.md`;
3. при bootstrap-команде прочитать `.codex/PROMT.md` stack по локальному контракту;
4. учитывать, что `_mcp_launchers/*` и `.aimemo/*` уже являются рабочей инфраструктурой;
5. менять agent-environment только точечно и с сохранением существующей схемы.
