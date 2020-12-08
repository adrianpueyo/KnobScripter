# KnobScripter
KnobScripter 2.4 is a full Python script editor for Nuke that can script on .py files and python knobs, with all the functionality from the default script editor plus syntax helpers.

You can also find a video of the tool [here](https://vimeo.com/adrianpueyo/knobscripter2) and one with the v2.1 updates [here](https://vimeo.com/adrianpueyo/knobscripter2-v1).

![KnobScripter sample image](https://user-images.githubusercontent.com/24983260/101388155-da75e300-38bf-11eb-895c-bbe6837325a2.png)

## Features
- **Full scripting mode for .py files.**
You can create, browse, modify or toggle between python files and folders.
- **Node editing mode**, to script directly on python buttons or callback knobs.
- **Python output console:** Same as the one from Nuke’s default script editor, where you can execute any code.
- **Find-Replace.** A proper find-replace widget as you’d expect in a python editor.
- **Snippets!** They are short codes you can assign to longer pieces of codes, so that by writing the short code and pressing tab you’ll get the long code.
- Python syntax highlighting, line numbers, auto-intending, auto-completer.
- Syntax helpers, multi-line commenting, moving/duplicating lines, and more!



## Installation

### A. Fresh install
1. Copy the `KnobScripter` folder and paste it inside your ​.nuke​ directory.
2. Open the file `menu.py` inside your .nuke folder with a text editor, or create it if it doesn’t exist.
3. Add the following line:
```python
import KnobScripter
```
4. Restart nuke.

### B. Updating KnobScripter
1. Replace the `KnobScripter` folder inside your ​.nuke​ directory.
2. Restart nuke.

## Usage
In Nuke, you can open the **KnobScripter** both as a floating window or as a dockable pane.
- To open the KnobScripter as a **floating window**, simply press `Alt+Z` on the Node
Graph.
- In order to bring the **dockable pane** you need to do the following:
Right click on the pane selection bar, and go to:
`Windows -> Custom -> KnobScripter`.
Then, a KnobScripter pane will get created. Now you can even save the workspace, so the KnobScripter will be created by default when you open nuke.

## Contributing
Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.

Please make sure to update tests as appropriate.

Thanks to the awesome Nuke community! Hope you enjoy this.
