# KnobScripter
**KnobScripter v3.0** (or **KS3**) is a full script editor for Nuke that can script python on .py files and knobs as well as BlinkScript, with all the functionality from the default script editor in Nuke plus syntax helpers, predictions, snippets and other handy features.
 
**KS3** is the next major step for this tool, and it features a greatly optimized code, Python 3 compatibility, BlinkScript mode, a Code Gallery and many other features and fixes.

- **Video Tutorial**: You can watch a [full video tutorial of the tool here](https://adrianpueyo.com/ks3-video).
- **Docs**: A complete user guide can be found at https://adrianpueyo.com/ks3-docs

![KS3_overview-768x374](https://user-images.githubusercontent.com/24983260/165090431-b179f3a0-8e22-4e92-b544-5d6f10e677fc.png)
<br />

## Features
- **Full scripting mode for .py files.**
You can create, browse, modify or toggle between python files and folders.
- **Node editing mode**, to script directly on python buttons or callback knobs, as well as BlinkScript.
- **Python output console:** Same as the one from Nuke’s default script editor, where you can execute any code.
- **Find-Replace.** A proper find-replace widget as you’d expect in a python editor.
- **Snippets!** They are short codes you can assign to longer pieces of codes, so that by writing the short code and pressing tab you’ll get the long code.
- **Code Gallery.**
The Code Gallery is a new way to store and browse through codes that you might want to revisit many times as reference.It includes a basic system of archiving. Then you can quickly browse and sort through the different codes you saved, while folding categories and reading descriptions.
- Python syntax highlighting, line numbers, auto-intending, auto-completer.
- Syntax helpers, multi-line commenting, moving/duplicating lines, and more!  
<br />

## Installation

### A. Fresh install
1. Copy the `KnobScripter` folder and paste it somewhere in your Nuke plugin path. For example, inside `Users/YourUser/.nuke` directory.
2. Open with a text editor the file `menu.py` that lives next to your `KnobScripter` folder, or create one if it doesn’t exist.
3. Add the following line:
```python
import KnobScripter
```
4. Restart Nuke.

### B. Updating KnobScripter
1. Replace the `KnobScripter` folder with the updated one.
2. Restart Nuke.
<br />

## Usage
In Nuke, you can open the **KnobScripter** both as a floating window or as a dockable pane.
- To open the KnobScripter as a **floating window**, simply press `Alt+Z` on the Node
Graph.
- In order to bring the **dockable pane** you need to do the following:
Right click on the pane selection bar, and go to:
`Windows -> Custom -> KnobScripter`.
Then, a KnobScripter pane will get created. Now you can even save the workspace, so the KnobScripter will be created by default when you open nuke.
<br />

## Contributing
Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.

Please make sure to update tests as appropriate.

Thanks to the awesome Nuke community! Hope you enjoy this.
