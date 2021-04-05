import os

KS_DIR = os.path.dirname(__file__)
ICONS_DIR = os.path.join(KS_DIR, "icons")

# TODO Redo the whole preferences loading and saving methods and interfaces
prefs = {
    "ks_directory" : "KS3",
    "ks_py_scripts_directory": "Scripts",
    "ks_blink_directory": "Scripts",
    "ks_snippets_file": "Snippets.txt",
    "ks_prefs_file": "Prefs.txt",
    "ks_state_file": "State.txt",
    "ks_default_size": [800,500],
    "ks_run_in_context": True,
    "ks_show_knob_labels": True,
    "code_style_python": "monokai",
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
py_scripts_dir = None
blink_dir = None
snippets_txt_path = None
prefs_txt_path = None
state_txt_path = None

script_editor_font = None
