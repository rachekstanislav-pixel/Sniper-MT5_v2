# Sniper Manager 3.6.5 Stage 1 BASE 65/35

Текущая сборка: **[Sniper_Manager_v3_6_5_STAGE1_BASE_65_35.mq5](Sniper_Manager_v3_6_5_STAGE1_BASE_65_35.mq5)**. Основа — RESTORED_STOP_FIX, прежние версии сохранены. Все модули включены. Настройки встроены в MQ5; SET не нужен. Тестировать GOLD/M5.

BASE: зона из 8 свечей, линия 50%, Buy Stop на 65% и Sell Stop на 35% от нижней границы. Стопы за зоной с регулируемым отступом 50 пипс. Новые сделки BASE сопровождаются по теням последних пяти закрытых M5-свечей, без безубытка и фиксированного TP. После +1000 пипс закрывается половина допустимого объёма, остаток сопровождается тралом. [Все правила, единицы цены и ограничения](STAGE1_BASE_65_35.md).

```sh
python3 tests/check_stage1_base.py
python3 tests/check_stage1_management.py
python3 tests/check_stage1_regressions.py
```

Это проверки реальных извлечённых функций с имитацией MT5 API, не компиляция MetaEditor и не исторический прогон MT5. EX5 здесь не собирался.

---

## Архив: описание RESTORED_STOP_FIX и предыдущих режимов

Следующие настройки и SET относятся к старым сборкам, а не к текущему первому этапу.

# Sniper Manager 3.6.5 Restored Stop Fix

Восстановлена база до V3: коммит 7d9c819, прежние интерфейс и алгоритмы. Узкая правка H4-реконструкции устраняет воспроизведённую блокировку входов. [Подробности](RESTORED_STOP_FIX.md).

Последняя сборка: **`Sniper_Manager_v3_6_5_RESTORED_STOP_FIX.mq5`**, тестировать на M5; отдельный SET не требуется. Все шесть модулей включены в исходнике. [Предыдущий разбор журналов](M5_LOG_REVIEW.md).

Полная автономная рабочая версия советника MetaTrader 5 на базе 3.6.5 VISUAL_AUDIT. Алгоритм 3.6.6 не переносился.

- Общий адаптивный детектор BASE: окна 6–24 свечи, диапазон/ATR, направленность и перекрытие. [Правила и A/B-проверка](BASE_DETECTION.md).
- BASE поддерживает два режима: прежний вход после закрытия за зоной с ATR-тейком и новые Buy Stop/Sell Stop на границах с целью у ближайшего подтверждённого экстремума H1/H4. [Правила Stop-режима](BASE_STOP.md).
- SL за последним подтверждённым локальным экстремумом.
- В ATR-режиме TP от фактического входа на расстоянии 2 × ATR, с пересчётом по закрытым свечам; в Stop-режиме TP фиксируется у подтверждённого H1/H4-экстремума.
- Сохранены динамический лот, валидность/актуальность H4/D1, маржа/экспозиция, защита неопределённого исполнения и глобальный стоп. Для BASE Stop обе стороны по умолчанию разрешены независимо от направления H4/D1; другие модули сохраняют свои фильтры.
- В рабочую версию также включены прежние исправления компрессии и информационного блока.
- Новый OTE: свип D1 `.790`, закрытие M15 обратно за уровень, удержанный H4 OB; против H4 — половинный денежный риск. Подробные правила: [OTE_RECLAIM.md](OTE_RECLAIM.md).

## Файлы

`Sniper_Manager_v3_6_5_RESTORED_STOP_FIX.mq5` — полный исходник; дополнительные модули проекта не нужны.
`Sniper_Manager_v3_6_5_BASE_DETECT_2.mq5` — сохранённый предыдущий вариант адаптивного детектора.
`Sniper_Manager_v3_6_5_BASE_ATR.mq5` — сохранённая предыдущая версия (BASE-STOP-1, коммит 690fd23), для сравнения.
Стандартные библиотеки MT5: `Trade/Trade.mqh`, `Canvas/Canvas.mqh`.
`Sniper_v3_6_5_BASE_ATR_NO_EMA.set` — рабочие настройки.
`Sniper_v3_6_5_BASE_ONLY_TEST.set` — настройки для изолированной проверки BASE.
`Sniper_v3_6_5_OTE_ONLY_TEST.set` — только новый OTE для первого теста.
`Sniper_v3_6_5_OTE_RECLAIM_NO_EMA.set` — общий набор с новым OTE, без EMA.
Старый `BASE_ATR_NO_EMA.set` сохранён и оставляет прежний OTE по касанию. Для нового сценария загрузить новый SET.
`Sniper_v3_6_5_BASE_STOP_ONLY_TEST.set` — новый Stop-режим BASE без других модулей.
`Sniper_v3_6_5_BASE_STOP_NO_EMA.set` — общий набор с новым Stop-режимом и новым OTE, без EMA.
В исходнике по умолчанию `BaseUseStopOrders=true` и `BaseStopBothDirections=true`. Старые ATR-наборы явно закрепляют false; Stop-наборы закрепляют true. После выбора советника нажать «Сброс» для использования исходных значений без старого SET.
`Sniper_v3_6_5_BASE_ADAPTIVE_ONLY_TEST.set` — адаптивный BASE Stop с диагностикой.
`Sniper_v3_6_5_BASE_ADAPTIVE_NO_EMA.set` — общий набор с адаптивным BASE.
`Sniper_v3_6_5_BASE_LEGACY_ONLY_TEST.set` — контроль прежнего детектора для A/B.
Старые SET без `BaseAdaptiveDetection` используют новое значение по умолчанию true; false явно включает старый детектор.
`baseline/` — исходные вложения до правок, для регрессионных проверок.
Подробности поведения и ограничений: [BASE_ATR_REVIEW.md](BASE_ATR_REVIEW.md).

## MetaTrader 5

1. Поместить MQ5 в `MQL5/Experts`, скомпилировать в MetaEditor.
2. В Strategy Tester выбрать советник и загрузить нужный SET. Для воспроизведения примера — GOLD/M5 на том же участке истории.
3. Проверить журнал `SN365 BASE`, `SN364 ENTRY`, `SN35 SAFETY`, фактические SL/TP и пересчёт TP по закрытым свечам.

В наборах автоторговля включена как в исходном наборе. Проверки данных H4/D1 остаются обязательными. При BaseStopBothDirections=true направление H4/D1 не блокирует только BASE Stop; при false прежние фильтры направления возвращаются.

## Локальные проверки

Требуются Python 3 и g++ с поддержкой C++17:

```sh
python3 tests/check_base_atr.py
python3 tests/check_atr_management.py
python3 tests/check_ote_reclaim.py
python3 tests/check_base_stop_orders.py
python3 tests/check_base_stop_setup.py
python3 tests/check_base_stop_oco.py
python3 tests/check_base_detection.py
python3 tests/check_mixed_module_exposure.py
python3 tests/check_reported_cash_risk.py
python3 tests/check_h4_reconstruction.py
```

Тесты исполняют реальные извлечённые функции как C++ с имитацией MT5 API. Это не компиляция MQL5 и не прогон Strategy Tester. EX5 не включён: MetaEditor/MT5 в облачной среде отсутствуют.
