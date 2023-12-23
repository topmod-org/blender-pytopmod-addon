# Blender pytopmod addon

## Install

To install Add-on first download ```pytopmod-addon.py```. Then launch Blender, go to Edit > Preferences. From pop-up window go to Add-ons tab and click install Button at the top right corner. Locate the downloaded python script and click "Install Add-on".

After installation search for "TopMod Operations" in the same Add-on list and activate Add-on. Since this Add-on relies on packages from a git repository it needs to download and install dependencies, expand Add-on and click "Install Dependecies". In order to do this step you may need evelated permissions depending on your Blender installation and directory preferences.

## Use

Currently there are 3 functions:

### ```Triangular Subvidision```
In object mode you can directly use this function to subdvide mesh.

### ```Delete Edge```
In edit mode you can delete edges, to delete and edge you need choose a corner pair that is already connected, i.e. two pairs of vertex and face. ```((v1,f1), (v2,f2))```

Selection starts after pressing the button, select using the edit mode selection tools to save selection for specific vertex and faces use the following key strokes:

- ```v1```: ALT+1
- ```f1```: ALT+2
- ```v2```: ALT+3
- ```f2```: ALT+4

after selections are done operations will be applied automatically.

### ```Insert Edge```
In edit mode you can insert edges, to insert and edge you need choose a corner pair, i.e. two pairs of vertex and face. ```((v1,f1), (v2,f2))```

Selection starts after pressing the button, select using the edit mode selection tools to save selection for specific vertex and faces use the following key strokes:

- ```v1```: ALT+1
- ```f1```: ALT+2
- ```v2```: ALT+3
- ```f2```: ALT+4

after selections are done operations will be applied automatically.