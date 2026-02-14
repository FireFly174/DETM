# Public Repository Governance Guide (DETM)

Короткий практический гайд для владельца репозитория перед переключением в public.

## 1) Как «быть главным» в репозитории (Owner/Maintainer baseline)

1. **Оставь минимум людей с правами Admin**.
   - Идеально: 1–2 trusted maintainers.
2. Остальным выдай роль **Write** или **Triage** по необходимости.
3. Включи правило: все изменения в `main` только через Pull Request.
4. Для PR используй CODEOWNERS + обязательный review.

Рекомендуемая матрица ролей:

- **Admin**: настройки репозитория, branch protection, secrets, releases.
- **Maintain**: merge PR, labels/milestones, без полного контроля над критичными настройками.
- **Write**: рабочие ветки и PR.
- **Triage**: обработка issues/дискуссий без записи в код.

## 2) Что нужно ограничить сразу после публикации

## Branch protection (`main`)

Включи в GitHub Settings → Branches:

- Require a pull request before merging.
- Require approvals: минимум 1 (лучше 2 для критичных изменений).
- Dismiss stale approvals when new commits are pushed.
- Require status checks to pass before merging (`CI`, `torch-tests` и др.).
- Require branches to be up to date before merging.
- Block force pushes.
- Block branch deletion.

## Tag/release hygiene

- Делай релизы только из защищённой ветки.
- Используй signed tags (если возможно).
- Пиши release notes с рисками/известными ограничениями.

## Actions/CI permissions

В GitHub Settings → Actions:

- Workflow permissions: **Read repository contents** по умолчанию.
- Разрешение на запись токеном — только где реально нужно.
- Включи approval для внешних fork PR (если применимо).

## 3) Security минимум для публичного репо

1. Включи **Security Advisories** и (если доступно) Dependabot alerts.
2. Подключи secret scanning (GitHub Advanced Security либо внешний сканер в CI).
3. Запрети хранение секретов в repo и history:
   - использовать только GitHub Secrets / environment secrets;
   - если секрет утёк — rotate + purge history (filter-repo/BFG) + invalidate.
4. Добавь/проверь `SECURITY.md` и канал приватного disclosure (у вас уже есть).
5. Для релизов: фиксируй changelog и поддерживаемые версии.

## 4) Что делать с ветками

Практичное правило:

- **Долгоживущие**: только `main` (и опционально `release/*`, если нужен релизный поезд).
- **Короткоживущие**: `feat/*`, `fix/*`, `docs/*`, удаляются после merge.

Рекомендуемый процесс:

1. После merge включить auto-delete branch на GitHub.
2. Раз в неделю чистить stale-ветки без активности >30–60 дней.
3. Ветки экспериментов переносить в draft PR или в отдельный архивный репозиторий.

Команды для локальной уборки:

```bash
# обновить remote refs
git fetch --prune

# посмотреть локальные ветки, слитые в текущую
git branch --merged

# удалить локальные merged ветки (кроме main/work)
git branch --merged | rg -v "^(\*\s*)?(main|work)$" | xargs -r git branch -d
```

## 5) Минимальный регламент maintainer-а

- Все изменения через PR.
- Для рискованных изменений: минимум 2 reviewer-а.
- Еженедельный triage: issues, PR, stale branches, security alerts.
- Ежемесячный security review:
  - доступы collaborators/teams;
  - workflow permissions;
  - secrets and tokens inventory;
  - зависимые пакеты и advisories.

## 6) Быстрый чек перед переключением в Public

- [ ] Branch protection на `main` включён и протестирован.
- [ ] Нет секретов в истории/файлах.
- [ ] Security advisory канал работает.
- [ ] CI обязателен перед merge.
- [ ] Включён auto-delete merged branches.
- [ ] README/CONTRIBUTING/SECURITY/SUPPORT актуальны.

