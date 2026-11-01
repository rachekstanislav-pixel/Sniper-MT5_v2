"""Reuse established regression scenarios against the NEW Stage1 source, not the old release."""
from pathlib import Path
root=Path(__file__).resolve().parents[1]
for name in ('check_working_revision.py','check_ote_reclaim.py','check_mixed_module_exposure.py','check_reported_cash_risk.py','check_h4_reconstruction.py'):
 path=root/'tests'/name
 code=path.read_text().replace('Sniper_Manager_v3_6_5_RESTORED_STOP_FIX.mq5','Sniper_Manager_v3_6_5_STAGE1_BASE_65_35.mq5')
 if name=='check_working_revision.py':
  code=code.replace("['IsBaseStopModule','DirectionAllowed'", "['IsStage1BaseModule','IsBaseStopModule','DirectionAllowed'")
 exec(compile(code,str(path),'exec'),{'__file__':str(path),'__name__':'__main__'})
