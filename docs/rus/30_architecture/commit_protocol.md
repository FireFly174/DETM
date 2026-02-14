# Телепортация и commit-протокол в DETM (канон)

## 1. Назначение документа

Данный документ вводит и фиксирует каноническое понятие **«телепортации»**, узаконенной протоколом согласования (commit-протоколом), в архитектуре DETM.

Под телепортацией понимается **допустимый перенос энергии, влияния или состояния через несколько внутренних шагов модели**, который на масштабе окна наблюдения (окна `N` в базовых тиках запуска) выглядит как мгновенное изменение, но при этом полностью согласован с внутренней динамикой и ограничениями уровней.

Документ описывает:

* различие между «идеальной траекторией» и локальной аппроксимацией,
* роль пакетов как носителей истины и отклонений,
* механизм масштабирования модели за счёт протокольной телепортации.

---

## 2. Граница публикации как основа консенсуса

В DETM канонической базовой единицей времени модели является `GlobalTick(L0)` (тик `L0`),
а в конкретном запуске допускается выбрать `base_level = Lmin` и считать время в `BaseTick(Lmin)` (см. `docs/rus/30_architecture/global_tick.md`),
а синхронизация внешнего мира (UI/логирование/интеграции) происходит на **границах публикации**,
заданных в единицах базового тика запуска.

На границе публикации:

* фиксируется согласованное состояние активного уровня,
* публикуются данные наружу,
* осуществляется согласование между независимыми вычислительными процессами.

Все события, происходящие *внутри* окна наблюдения, считаются внутренней динамикой и не обязаны быть наблюдаемыми напрямую.

---

## 3. Идеальная траектория и локальное приближение

Модель DETM различает два уровня описания движения энергии:

### 3.1 Идеальная траектория

**Идеальная траектория** - это последовательность состояний/артефактов, зафиксированных на границах публикации (в координатах базового тика запуска).

Она:

* согласована между всеми участниками,
* удовлетворяет ограничениям уровня,
* используется как «истина» (authoritative path).

### 3.2 Локальное приближение

Между границами публикации допускается:

* предсказание следующих состояний,
* интерполяция,
* упрощённая динамика без уточнения.

Это приближение может отличаться от идеальной траектории, но не считается ошибкой до момента commit.

---

## 4. Пакеты как элементы протокола

В архитектуре DETM пакеты являются **протокольными сущностями**, а не просто контейнерами данных.

Выделяются следующие типы пакетов:

### 4.1 Commit-пакет

Commit-пакет фиксирует результат границы публикации, выраженной в координатах базового тика запуска.

Содержит:

* `base_level` (минимальный уровень запуска, например `L0` или `Ln-k`),
* номер базового тика `tick` (на котором сформирован commit),
* `window_ticks` / `publish_stride_ticks` (параметры наблюдения),
* согласованное состояние (или его сигнатуру),
* метаданные качества (бюджет уточнений, флаги деградации).

Commit-пакет подтверждает, что локальные предсказания оказались валидными *или* были скорректированы.

---

### 4.2 Correction-пакет

Correction-пакет фиксирует **отклонение от идеальной траектории**.

Он используется, когда:

* локальное приближение не совпало с результатом уточнения,
* произошёл переход через уровень,
* была применена дополнительная динамика (refinement).

Correction-пакет может содержать:

* локальные дельты состояния,
* замены патчей,
* указание на область и тип отклонения.

Correction-пакеты формируют эмпирическое знание системы о сложных переходах.

---

### 4.3 Influence-пакет

Influence-пакет описывает **внешнее или внутреннее влияние**, которое должно быть встроено в симуляцию получателя (в координатах `GlobalTick` и/или окон наблюдения).

Принципиально:

> Influence-пакет после получения **становится частью реальности получателя**,
> а не продолжением вычислений отправителя.

Он:

* привязывается к номеру глобального тика,
* содержит правила действия (маска, направление, интенсивность, время жизни),
* далее участвует в детерминированной динамике получателя.

---

## 5. Телепортация как следствие протокола

На масштабе окна наблюдения эффекты, накопленные за множество внутренних шагов, проявляются как **мгновенный перенос**.

Это выглядит как:

* скачок энергии,
* внезапное появление/исчезновение структуры,
* изменение конфигурации без видимой промежуточной динамики.

Такой эффект **не является нарушением физики модели**, а является:

> следствием согласования идеальной траектории через commit-протокол.

Этот механизм и называется **протокольной телепортацией**.

---

## 6. Связь с масштабированием модели

Телепортация делает возможным масштабирование DETM:

* внутренние процессы могут происходить на более мелких уровнях и частотах,
* наружу публикуется только согласованный результат,
* сложные переносы энергии отображаются как волновые или нелокальные эффекты.

Если система способна:

* предсказать несколько шагов вперёд,
* подтвердить эти предсказания на уточнённом уровне,

то на масштабе окна наблюдения это эквивалентно **нелокальному переносу**, наблюдаемому как волновая функция или телепортация.

---

## 7. Роль телепортации в обучении и ускорении

Correction-пакеты, возникающие при телепортации:

* фиксируют, где и почему локальное приближение оказалось неверным,
* образуют набор типовых отклонений,
* используются для ускорения будущих шагов.

Со временем:

* локальные предсказания становятся точнее,
* количество correction-пакетов уменьшается,
* телепортация становится «ожидаемым» поведением уровня.

---

## 8. Межнодовая синхронизация тиков (node/fabric)

Для распределённого контура DETM фиксируется принцип:

* синхронизация выполняется на **границе commit** (`GlobalTick/epoch`),
* внутренние microsteps ноды не обязаны быть глобально синхронными.

То есть:
* нода живёт автономно внутри тика,
* наружу публикует commit-артефакт в координатах общего времени,
* fabric-координатор согласует commit’ы по `epoch/watermark`, а не по “внутренним кадрам” ноды.

Это сохраняет канон асинхронности и обеспечивает воспроизводимость межнодового обмена.

---

## 9. Commit как атомарный факт изменения

В node/fabric режиме commit трактуется как минимально достаточный проверяемый пакет изменения:

* `parent_ref` — ссылка на предыдущий commit в цепочке узла,
* `tick_ref` — координата времени (`base_level`, `tick`, опционально `equiv_L0_ticks`),
* `inputs_ref` — входы/команды/влияния, применённые в окне,
* `delta_ref` — ссылка на дельту или агрегированный результат,
* `invariants_ref` — проверяемые инварианты/ограничения шага,
* `summary` — компактные метрики для индексации/маршрутизации (в т.ч. `epoch`/`watermark` для fabric-coordination),
* `trace_ref` — ссылка на канонический журнал commit,
* `signature` — подпись автора commit (узла/рантайма).

Минимальная machine-validatable схема (MVP в коде):
* `detm/runtime/commit_packet.py` (`CommitPacket`, `CommitTickRef`)
* `detm/runtime/schemas.py` (`commit_packet` schema registry)
* `detm/runtime/fabric/envelope.py` (`FabricEnvelope`: `message_type/channel/mode/payload_ref`, optional `payload_inline` bridge)
* `detm/runtime/fabric/ack.py` (`ProofAck`, `TrustAck`: validator acknowledgements)
* `detm/runtime/commit_chain.py` (`CommitChainManager`: `tail -> parent_ref` sequencing)
* `detm/runtime/fabric/transport/*` (`InMemoryFabricBus`, `BufferedFabricTransport`: topic routing + live backpressure adapter)
* `detm/runtime/fabric/validator/*` (`FabricValidator`, `LocalFabricValidator`: chain checks + replay-check sampling policy)
* `detm/runtime/fabric/handshake/*` (`FabricHandshakeService`: commit envelope -> ack envelopes, mode-aware channel routing + delivery-ack emission)
* `detm/runtime/fabric/ack_ingress.py` (`FabricAckIngressService`: proof/trust ack subscription + ingress forwarding в quorum)
* `detm/runtime/fabric/quorum_runtime.py` (`FabricQuorumRuntimeService`: quorum policy selection + validator registry + runtime snapshot composition)
* `detm/runtime/fabric/quorum_report.py` (`FabricQuorumReportBuilder`: runtime-композиция секций quorum-report, delivery-report, replay-report)
* `detm/runtime/fabric/report_writer/*` (`FabricRuntimeReportWriter`: runtime-запись ack/delivery-ack/dead-letter и quorum-report артефактов)
* `detm/runtime/fabric/runtime_bundle.py` (`FabricHandshakeRuntimeBundle`: lifecycle-порядок запуска/остановки runtime-компонентов handshake)
* `detm/runtime/fabric/runtime_composer/*` (`compose_fabric_handshake_runtime`: factory/composer сборки runtime-компонентов handshake)
* `detm/runtime/fabric/artifact_resolver.py` (`FabricArtifactResolver`: commit/ack artifact write+resolve + replay-check adapter)
* `detm/runtime/fabric/handshake_recorder_config/*` (`normalize_fabric_handshake_recorder_attach_kwargs`: вынос нормализации attach-конфига из subscriber)
* `detm/runtime/fabric/runtime_helpers.py` (`mode_channels/channel_for_mode/start_runtime_bundle`: helper-утилиты runtime wiring)
* `detm/runtime/fabric/delivery/*` (`JsonlFabricEnvelopeOutbox`: file-backed undelivered envelope queue + flush/retry + overflow backpressure policy)
* `detm/runtime/fabric/delivery_receipts/*` (`CountDeliveryReceiptPolicy`, `ValidatorSetDeliveryReceiptPolicy`, `InMemoryDeliveryReceiptCoordinator`)
* `detm/runtime/fabric/delivery_tracking/*` (`DeliveryTrackingCoordinator`: retry/timeout delivery state-machine)
* `detm/runtime/fabric/commit_delivery/*` (`FabricCommitDeliveryService`: commit publish/retry/outbox + `delivery_ack` subscription wiring)
* `detm/runtime/fabric/commit_ingress.py` (`FabricCommitIngressService`: commit packet ingress -> artifact resolve -> envelope publish)
* `detm/runtime/fabric/epoch/*` (`FabricEpochCoordinator`, `InMemoryEpochWatermarkCoordinator`, `FileEpochWatermarkCoordinator`, `ReplicatedFileEpochWatermarkCoordinator`: commit boundary epoch/watermark gate + lock/quorum policy)
* `detm/runtime/fabric/epoch_consensus/*` (`TransportEpochConsensusCoordinator`: `epoch_proposal/epoch_vote` pre-consensus over transport)
* `detm/runtime/fabric/quorum/*` (`QuorumPolicy`, `BasicQuorumPolicy`, `ValidatorSetQuorumPolicy`, `InMemoryQuorumCoordinator`)
* `detm/runtime/fabric/validator_registry.py` (`ValidatorRegistry`, `StaticValidatorRegistry`: membership source for quorum policies)
* `detm/runtime/fabric/artifact_store.py` (`FabricArtifactStore`, `FileFabricArtifactStore`: durable commit/ack resolver)
* `detm/runtime/fabric/tcp_transport/*` (`TcpFabricTransport`, `TcpFabricRelay`, `open_fabric_transport`)
* `detm_app/runtime/subscribers/fabric/*` (`FabricHandshakeRecorder`: runtime wiring + `fabric_acks.jsonl`, split-mode channel policy)
* `detm_app/runtime/subscribers/commit/stream.py` (`CommitJsonlWriter`, `commits.jsonl`, linkage через `trace_ref`)
* `detm/runtime/level_policy/*` (`audit_commit_enabled`, `audit_commit_stride`) для policy-driven `commits_audit.jsonl`
* `detm/runtime/fabric/validation/*` + `commit_validation.json` (local chain/proof/watermark validator report)

---

## 10. Режимы commit-публикации

### 10.1 Realtime commit (тонкий)

Используется для онлайновой маршрутизации и low-latency наблюдаемости:

* минимальный `delta_ref`,
* краткий набор инвариантов,
* компактный `summary`,
* публикация по `commit_stride`.

### 10.2 Audit commit (толстый)

Используется для реплея/валидации/разбора:

* периодические снапшоты состояния,
* расширенный набор инвариантов/свидетельств,
* расширенные метаданные для оффлайн проверки.

---

## 11. Канонические типы commit-пакетов

В node/fabric контуре фиксируются четыре типа:

* `StateCommit` — локальная цепочка узла (реплей, откат, аудит).
* `BoundaryCommit` — межнодовый обмен через границу (`OuterFields`, возмущения, потоки), без передачи полного state.
* `CoarsenedCommit` — публикация агрегатов `L0 -> Ln` для верхних уровней и подписчиков.
* `ProofCommit` — пакет для валидации (подпись, parent-chain, инварианты, опционально выборочный replay-check).

---

## 12. Роль fabric-координатора

Координатор/fabric не подменяет физику узлов и не исполняет шаг за ноду.
Его ответственность:

* принимать commit’ы и валидировать протокольные поля,
* контролировать последовательность `parent_ref`/`tick_ref`,
* вести `epoch/watermark` согласования между нодами,
* маршрутизировать commit-артефакты подписчикам по типам данных.

Это аналог “relay + validator + time coordinator”, а не “центральный симулятор”.

---

## 13. Практический профиль transport/packet (legacy extraction)

Анализ `D:\github\game\references\old_repo\lib` подтверждает применимость нескольких паттернов
для этапа `Node/Fabric`, при этом без прямого копирования кода.

Что переносится в канон:

* `network/ledger/AJWSPackageRequest.py`:
  envelope-идея `type/listener/data` фиксируется как `FabricEnvelope`
  (`type/channel/mode/payload_ref`) для маршрутизации commit/event сообщений.
* `ledger/package/PackageManager.py`:
  цепочка `tail -> parent` фиксируется как `CommitChainManager`
  (`sequence`, `parent_ref`, базовая верификация последовательности).
* `ledger/package/PackageJSONEncoder.py` + `PackageJSONDecoder.py`:
  фиксируется принцип симметричного typed codec для сериализации/десериализации commit payload.
* `ledger/package/PackageTrust.py`:
  фиксируется отдельный trust/proof acknowledgement пакет (`ProofAck/TrustAck`)
  как граница ответственности validator/fabric.
* `publisher/Publisher.py`:
  фиксируется минимальный pub/sub-dispatch по типу события как transport-модель подписчиков fabric.

Текущее состояние реализации в DETM (MVP):
* `FabricEnvelope` + `InMemoryFabricBus` добавлены как базовый контракт и topic-routing слой.
* `CommitChainManager` добавлен как stateful lifecycle-класс цепочки commit.
* `ProofAck/TrustAck` добавлены как отдельные validator acknowledgement contracts.
* `FabricHandshakeService` встроен в runtime как opt-in wiring через `FabricHandshakeRecorder`/CLI.
* Добавлены локальные quorum/retry/timeout primitives (`BasicQuorumPolicy`, `ValidatorSetQuorumPolicy`, `RetryPolicy`) и отчёт `fabric_quorum_report.json`.
* Добавлен `InMemoryEpochWatermarkCoordinator` и handshake-gate:
  commit сначала проходит проверку монотонности `tick/epoch/watermark`, затем попадает в validator chain/proof checks.
* Добавлен `FileEpochWatermarkCoordinator` как shared-state MVP для межнодового согласования `epoch/watermark` через общий state-файл.
* Для `FileEpochWatermarkCoordinator` добавлен lock-контур (timeout/poll/stale cleanup) для межпроцессного доступа к shared state.
* Добавлен `ReplicatedFileEpochWatermarkCoordinator` (read/write quorum по нескольким state-файлам) как pre-consensus replicated MVP.
* Добавлен transport pre-consensus слой `TransportEpochConsensusCoordinator` (`epoch_proposal/epoch_vote`) для кворумного `epoch`-решения без shared storage.
* Добавлен replay-check sampling в `LocalFabricValidator` (policy-driven, с runtime отчётом в `fabric_quorum_report.json`).
* Добавлен `StaticValidatorRegistry` как MVP-источник validator membership для quorum-политик.
* Добавлен file-backed shared artifact resolver (`FileFabricArtifactStore`) для `commit_ref/payload_ref` разрешения между нодами.
* Добавлен network bridge `payload_inline` для `commit/ack` envelope-сообщений:
  при отсутствии shared artifact resolver валидатор/координатор может взять payload напрямую из envelope.
* Добавлен network transport MVP (`TcpFabricTransport`/`TcpFabricRelay`) для node-to-node маршрутизации envelope-сообщений.
* Добавлен mode-split routing `realtime/audit` для node-to-node handshake:
  отдельные каналы `commit/ack` по режимам (опционально, с обратной совместимостью shared-channel режима).
* Добавлен file-backed delivery outbox (`JsonlFabricEnvelopeOutbox`) и runtime wiring:
  недоставленные `commit/ack` envelope складываются в локальную очередь и переотправляются через `flush` при следующих publish-циклах.
* Добавлена policy деградации при overflow outbox (`audit_first|oldest|newest`), где `audit_first` позволяет сохранять приоритет realtime-потока под перегрузкой.
* Добавлен live transport backpressure-adapter (`BufferedFabricTransport`) с политиками `block/drop_oldest/drop_newest/fail` для ограничения очереди publish-path.
* Добавлен acknowledged-delivery MVP для commit-envelope:
  `delivery_id` в `FabricEnvelope`, `delivery_ack` channel, receipt tracking
  (`required receipts`, `retry/timeout`, `validator-set enforcement`, `reject_on_any_reject`) в `FabricHandshakeRecorder`.
* Delivery receipt policy вынесен в отдельный coordinator-layer
  (`InMemoryDeliveryReceiptCoordinator` + policy classes), чтобы разделить transport-wiring и решение по receipts.
* Retry/timeout state-machine для tracked delivery вынесен из subscriber-слоя в runtime
  (`DeliveryTrackingCoordinator`), чтобы уменьшить orchestration-логику в `FabricHandshakeRecorder`.
* Commit-delivery routing (`publish/retry/outbox + delivery_ack subscribe/consume`) вынесен
  в runtime service `FabricCommitDeliveryService`, чтобы зафиксировать отдельную границу ответственности
  между fabric-runtime и subscriber-orchestration.
* Proof/trust ack ingress (`ack subscribe/consume + forwarding to quorum`) вынесен
  в runtime service `FabricAckIngressService`, чтобы убрать transport-subscription логику
  из `FabricHandshakeRecorder` и оставить subscriber-слой orchestration-only.
* Quorum composition (`policy selection + validator registry + pending-timeout snapshot fields`) вынесена
  в runtime service `FabricQuorumRuntimeService`, чтобы убрать policy-construction из `FabricHandshakeRecorder`
  и зафиксировать единый runtime-компонент ack-aggregation.
* Сборка `fabric_quorum_report.json` вынесена в runtime builder `FabricQuorumReportBuilder`,
  чтобы отделить report-композицию (artifact/outbox/backpressure/delivery/epoch/replay sections)
  от orchestration-кода `FabricHandshakeRecorder`.
* Запись runtime-артефактов (`fabric_acks.jsonl`, `fabric_ack_envelopes.jsonl`,
  `fabric_delivery_acks.jsonl`, `fabric_quorum_report.json`, `fabric_dead_letters.json`)
  вынесена в `FabricRuntimeReportWriter`, чтобы отделить persistence-слой от lifecycle orchestration.
* Lifecycle wiring (`start/stop` порядок для `FabricHandshakeService`, `FabricAckIngressService`,
  `FabricCommitDeliveryService`, transport close, epoch-consensus stop) вынесен в
  `FabricHandshakeRuntimeBundle`, чтобы убрать дублирование orchestration-кода из `FabricHandshakeRecorder`.
* Factory-сборка runtime-компонентов (`transport/outbox/validator/epoch/quorum/ack-ingress/delivery/report/bundle`)
  вынесена в `compose_fabric_handshake_runtime`, чтобы сократить `FabricHandshakeRecorder.attach`
  до роли thin-adapter к runtime-composition.
* Commit/ack artifact write+resolve и replay-check статистика вынесены в `FabricArtifactResolver`,
  чтобы убрать artifact/replay bookkeeping из `FabricHandshakeRecorder` и переиспользовать
  единый runtime adapter в composer + handshake/quorum callbacks.
* Mode-channel routing и запуск runtime-bundle вынесены в `fabric_runtime_helpers.py`,
  чтобы убрать дублирование мелкой channel/lifecycle логики и держать `FabricHandshakeRecorder`
  как thin adapter поверх runtime-компонентов.

Что не переносится as-is:

* `scheduler/*` из legacy-репозитория: незавершённый/недетерминированный контур,
  не соответствует канону синхронизации DETM по `commit boundary`.
* `network/server/AJConnectionService.py` в текущем виде:
  упрощённый relay (например, отправка в первого клиента) не подходит для production fabric.

Итог:
legacy-код рассматривается как источник протокольных паттернов и терминов,
а реализация в DETM должна быть заново собрана под канонические ограничения
(`GlobalTick/epoch/watermark`, `realtime/audit`, `trace_ref`, deterministic replay).

---

## 14. Краткое резюме (канон)

* Глобальный тик задаёт границы согласованной реальности.
* Межнодовая синхронизация идёт по commit boundary, а не по внутренним microsteps.
* Пакеты являются элементами протокола, а не просто данными.
* Commit-пакеты фиксируют истину; Correction-пакеты фиксируют расхождения.
* `State/Boundary/Coarsened/Proof` commit-ы покрывают локальный, межнодовый и валидационный контуры.
* Realtime/Audit режимы разделяют низкую задержку и глубокую проверку.
* Influence-пакеты встраиваются в реальность получателя.
* Телепортация — допустимый эффект согласования на масштабе глобального тика.
* Этот механизм является ключом к масштабированию DETM и node/fabric горизонту.

Данный протокол является каноническим и используется во всех дальнейших архитектурных решениях проекта.












