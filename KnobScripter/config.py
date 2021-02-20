import os

KS_DIR = os.path.dirname(__file__)
ICONS_DIR = os.path.join(KS_DIR, "icons")

scripts_dir = os.path.expandvars(os.path.expanduser("~/.nuke/KnobScripter_Scripts"))
blink_dir = os.path.expandvars(os.path.expanduser("~/.nuke/KnobScripter_Scripts"))
snippets_txt_path = os.path.expandvars(os.path.expanduser("~/.nuke/KnobScripter_Snippets.txt"))
prefs_txt_path = os.path.expandvars(os.path.expanduser("~/.nuke/KnobScripter_Prefs.txt"))
state_txt_path = os.path.expandvars(os.path.expanduser("~/.nuke/KnobScripter_State.txt"))

# TODO Redo the whole preferences loading and saving methods and interfaces
prefs = {
    "ks_default_size": [800,500],
    "ks_run_in_context": True,
    "ks_show_knob_labels": True,
    "code_style_python": "sublime",
    "code_style_blink": "default",
    "se_style": "default",
    "se_font_family": "Monospace",
    "se_font_size": 10,
    "se_tab_spaces": 4,
    "qt_btn_size": 24,
    "qt_icon_size": 17,
}

script_editor_styles = {
    "default": {
        "stylesheet": 'background:#282828;color:#EEE;',
        "selected_line_color": (62, 62, 62, 255),
        "lineNumberAreaColor": (36, 36, 36),
        "lineNumberColor": (110, 110, 110),
        "currentLineNumberColor": (255, 170, 0),  # TODO: add scrollbar color
    },
    "blink_default": {
        "stylesheet": 'background:#505050;color:#DEDEDE;',
        "selected_line_color": (110, 110, 110, 255),
        "lineNumberAreaColor": (72, 72, 72),
        "lineNumberColor": (34, 34, 34),
        "currentLineNumberColor": (255, 255, 255),
    }
}

# Initialized at runtime
script_editor_font = None