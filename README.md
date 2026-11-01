# Sniper Manager 3.6.5 BASE DETECT 2

Полная автономная рабочая версия советника MetaTrader 5 на базе 3.6.5 VISUAL_AUDIT. Алгоритм 3.6.6 не переносился.

- Общий адаптивный детектор BASE: окна 6–24 свечи, диапазон/ATR, направленность и перекрытие. [Правила и A/B-проверка](BASE_DETECTION.md).
- BASE поддерживает два режима: прежний вход после закрытия за зоной с ATR-тейком и новые Buy Stop/Sell Stop на границах с целью у ближайшего подтверждённого экстремума H1/H4. [Правила Stop-режима](BASE_STOP.md).
- SL за последним подтверждённым локальным экстремумом.
- В ATR-режиме TP от фактического входа на расстоянии 2 × ATR, с пересчётом по закрытым свечам; в Stop-режиме TP фиксируется у подтверждённого H1/H4-экстремума.
- Сохранены динамический лот, валидность/актуальность H4/D1, маржа/экспозиция, защита неопределённого исполнения и глобальный стоп. Для BASE Stop обе стороны по умолчанию разрешены независимо от направления H4/D1; другие модули сохраняют свои фильтры.
- В рабочую версию также включены прежние исправления компрессии и информационного блока.
- Новый OTE: свип D1 `.790`, закрытие M15 обратно за уровень, удержанный H4 OB; против H4 — половинный денежный риск. Подробные правила: [OTE_RECLAIM.md](OTE_RECLAIM.md).

## Файлы

`Sniper_Manager_v3_6_5_BASE_DETECT_2.mq5` — полный исходник; дополнительные модули проекта не нужны.
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
```

Тесты исполняют реальные извлечённые функции как C++ с имитацией MT5 API. Это не компиляция MQL5 и не прогон Strategy Tester. EX5 не включён: MetaEditor/MT5 в облачной среде отсутствуют.
