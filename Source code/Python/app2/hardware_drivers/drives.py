from .drive import build_drive

female1_o_drive = build_drive(name="female1/o drive", start_value=300)
female1_p_drive = build_drive(name="female1/p drive", start_value=1200)

female2_o_drive = build_drive(name="female2/o drive", start_value=600)
female2_p_drive = build_drive(name="female2/p drive", start_value=600)

female3_o_drive = build_drive(name="female3/o drive", start_value=1200)
female3_p_drive = build_drive(name="female3/p drive", start_value=300)

drives = (
    female1_o_drive,
    female1_p_drive,
    
    female2_o_drive,
    female2_p_drive,
    
    female3_o_drive,
    female3_p_drive,
)
    


