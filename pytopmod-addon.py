bl_info = {
    "name": "TopMod Operations",
    "author": "Tolga Yildiz",
    "version": (0, 1, 0),
    "blender": (3, 0, 0),
    "location": "View3D > Sidebar > TopMod",
    "description": "TopMod",
    "warning": "Requires installation of dependencies",
    "category": "3D View"
    }
    
import bpy
import bmesh
import os
import sys
import subprocess
import importlib
import shutil
from collections import namedtuple

Dependency = namedtuple("Dependency", ["module", "package", "name"])

dependencies = (Dependency(module="pytopmod", package=None, name=None),)

dependencies_installed = False

def import_module(module_name, global_name=None, reload=True):
    """
    Import a module.
    :param module_name: Module to import.
    :param global_name: (Optional) Name under which the module is imported. If None the module_name will be used.
       This allows to import under a different name with the same effect as e.g. "import numpy as np"
    :raises: ImportError and ModuleNotFoundError
    """
    if global_name is None:
        global_name = module_name

    if global_name in globals():
        importlib.reload(globals()[global_name])
    else:
        # Attempt to import the module and assign it to globals dictionary. This allow to access the module under
        # the given name, just like the regular import would.
        globals()[global_name] = importlib.import_module(module_name)

def install_pip():
    """
    Installs pip if not already present. Please note that ensurepip.bootstrap() also calls pip, which adds the
    environment variable PIP_REQ_TRACKER. After ensurepip.bootstrap() finishes execution, the directory doesn't exist
    anymore. However, when subprocess is used to call pip, in order to install a package, the environment variables
    still contain PIP_REQ_TRACKER with the now nonexistent path. This is a problem since pip checks if PIP_REQ_TRACKER
    is set and if it is, attempts to use it as temp directory. This would result in an error because the
    directory can't be found. Therefore, PIP_REQ_TRACKER needs to be removed from environment variables.
    """

    try:
        # Check if pip is already installed
        subprocess.run([sys.executable, "-m", "pip", "--version"], check=True)
    except subprocess.CalledProcessError:
        import ensurepip

        ensurepip.bootstrap()
        os.environ.pop("PIP_REQ_TRACKER", None)

def install_and_import_module(module_name, package_name=None, global_name=None):
    """
    Installs the package through pip and attempts to import the installed module.
    :param module_name: Module to import.
    :param package_name: (Optional) Name of the package that needs to be installed. If None it is assumed to be equal
       to the module_name.
    :param global_name: (Optional) Name under which the module is imported. If None the module_name will be used.
       This allows to import under a different name with the same effect as e.g. "import numpy as np"
    :raises: subprocess.CalledProcessError and ImportError
    """
    if package_name is None:
        package_name = module_name

    if global_name is None:
        global_name = module_name

    environ_copy = dict(os.environ)
    environ_copy["PYTHONNOUSERSITE"] = "1"

    subprocess.run([sys.executable, "-m", "pip", "install", package_name], check=True, env=environ_copy)

    import_module(module_name, global_name)
    
    
def pull_and_import_module(module_url, module_name, package_name=None, global_name=None):
    """
    Clones a python package repository and installs the package to the site-packages and attempts to import the installed module.
    :param module_url: Git repository.
    :param module_name: Module to import.
    :param package_name: (Optional) Name of the package that needs to be installed. If None it is assumed to be equal
       to the module_name.
    :param global_name: (Optional) Name under which the module is imported. If None the module_name will be used.
       This allows to import under a different name with the same effect as e.g. "import numpy as np" where "np" is
       the global_name under which the module can be accessed.
    :raises: subprocess.CalledProcessError and ImportError
    """
    curr_dir = os.getcwd()
    os.chdir(os.path.join(sys.prefix,'lib','site-packages'))
    os.system("git clone https://github.com/topmod-org/pytopmod-core.git")
    shutil.copytree(os.path.join(sys.prefix,"lib","site-packages","pytopmod-core","src","pytopmod"), os.path.join(sys.prefix,"lib","site-packages","pytopmod"))

def bpyToDLFL(bm = None):
    """
    Creates a DLFLMesh from the selected object in the viewport
    :return mesh: DLFLMesh.
    :return bm: BMesh object of the selected object.
    :return verts: Dictionary of BMesh vertices to DLFL vertex_key.
    :return faces: Dictionary of BMesh faces to DLFL face_key.
    """
    from pytopmod.core.dlfl.mesh import DLFLMesh

    bpy_object = bpy.context.object
    bpy_mesh = bpy.context.object.data
    if (bm == None):
        if(bpy.context.object.mode == 'EDIT'):
            bm = bmesh.from_edit_mesh(bpy_mesh)
        if(bpy.context.object.mode == 'OBJECT'):
            bm = bmesh.new()
            bm.from_mesh(bpy_mesh)
    

    mesh = DLFLMesh()
    bm.verts.ensure_lookup_table()
    
    faces = {}
    verts = {}
    for v in bm.verts:
        verts[v.index] = mesh.create_vertex(v.co)    
    
    i = 0
    for f in bm.faces:
        faces[f.index] = mesh.create_face()
    for f in bm.faces:
        for l in f.loops:
            mesh.face_vertices[faces[f.index]].append(verts[l.vert.index])
            
            start_l = l
            if faces[f.index] not in mesh.vertex_faces[verts[l.vert.index]]:                
                mesh.vertex_faces[verts[l.vert.index]].add(faces[f.index])
                
            l = l.link_loop_radial_next
            while(l != start_l):
                if faces[f.index] not in mesh.vertex_faces[verts[l.vert.index]]:
                    mesh.vertex_faces[verts[l.vert.index]].add(faces[f.index])
                l = l.link_loop_radial_next     

    return mesh, bm, verts, faces

def DLFLtoBPY(mesh):
    """
    Creates a Blender Mesh Data from the DLFLMesh mesh
    :param mesh: DLFLMesh.
    :return new_mesh: Blender Mesh Data.
    """
    vertex_index_map = {}
    obj_vertices = []
    for index, vertex in enumerate(mesh.vertex_keys):
        vertex_index_map[vertex] = index
        coordinates = (coord for coord in mesh.vertex_coordinates[vertex])
        obj_vertices.append(coordinates)
        
    obj_faces = []
    for face in mesh.face_keys:
        indices = [(vertex_index_map[vertex]) for vertex in mesh.face_vertices[face]]
        obj_faces.append(indices)
        
    new_mesh = bpy.data.meshes.new('new_mesh')
    new_mesh.from_pydata(obj_vertices, [], obj_faces)
    new_mesh.update()
    return new_mesh


class TOPMOD_OT_triangular_subdivision(bpy.types.Operator):
    bl_idname = "mesh.triangular_subdivision"
    bl_label = "Triangular Subdivision"
    bl_description = "This operator subdivides the selected object and creates a new object."
    bl_options = {"REGISTER"}
        
    @classmethod  
    def poll(cls, context):
        if (context.active_object is None):
            return False
        return context.active_object.mode == 'OBJECT'
    
    def execute(self, context):
        from pytopmod.core.dlfl.operations import subdivision
        mesh, bm, _, _ = bpyToDLFL()
        for face in list(mesh.face_keys):
            subdivision.triangulate_face(mesh, face)
        bm.free()
        mesh = DLFLtoBPY(mesh)
        context.object.data = mesh
        return {"FINISHED"}


class TOPMOD_OT_delete_edge(bpy.types.Operator):
    bl_idname = "mesh.topmod_delete_edge"
    bl_label = "Delete Edge"
    bl_description = "This operator deletes edges that are selected in the viewport."
    bl_options = {"REGISTER"}

    v1: bpy.props.IntProperty(name = "v1", description = "Index of first vertex",default=-1)
    v2: bpy.props.IntProperty(name = "v2", description = "Index of second vertex",default=-1)
    f1: bpy.props.IntProperty(name = "f1", description = "Index of first face",default=-1)
    f2: bpy.props.IntProperty(name = "f2", description = "Index of second face",default=-1)
    
    from bmesh.types import BMVert, BMFace, BMesh
    
    @classmethod  
    def poll(cls, context):
        if (context.active_object is None):
            return False
        return context.active_object.mode == 'EDIT'

    def execute(self, context):
        from pytopmod.core.dlfl import operators
        mesh, bm, verts, faces = bpyToDLFL()
        operators.delete_edge(mesh,verts[self.v1], faces[self.f1] , verts[self.v2], faces[self.f2])

        mesh = DLFLtoBPY(mesh)
        bpy.ops.object.editmode_toggle()
        context.object.data = mesh
        bpy.ops.object.editmode_toggle()
        bpy.ops.mesh.select_all(action='DESELECT')
        return {'FINISHED'}

    def modal(self, context, event):
        self.invoked = True
        if self.v1 != -1 and self.v2 != -1 and self.f1 != -1 and self.f2 != -1: 
            return self.execute(context)
        if not event.alt:
            if event.type in {'ONE', 'TWO', 'THREE', 'MOUSEMOVE', 'LEFTMOUSE','RIGHTMOUSE','WHEELDOWNMOUSE','MIDDLEMOUSE', 'WHEELUPMOUSE'}:
                return {'PASS_THROUGH'}
        if event.alt and event.type == 'ONE':  # Apply
            self.v1 = [v for v in bmesh.from_edit_mesh(context.object.data).verts if v.select][0].index
            return {'PASS_THROUGH'}
        elif event.alt and event.type == 'TWO':  # Apply
            self.f1 = [f for f in bmesh.from_edit_mesh(context.object.data).faces if f.select][0].index
            return {'PASS_THROUGH'}
        elif event.alt and event.type == 'THREE':  # Apply
            self.v2 = [v for v in bmesh.from_edit_mesh(context.object.data).verts if v.select][0].index
            return {'PASS_THROUGH'}
        elif event.alt and event.type == 'FOUR':  # Apply
            self.f2 = [f for f in bmesh.from_edit_mesh(context.object.data).faces if f.select][0].index
            return {'PASS_THROUGH'}
        elif event.type == 'ESC':
            return {'CANCELLED'}
        else:
            return {'PASS_THROUGH'}
        
        return {'RUNNING_MODAL'}
    def invoke(self, context, event):
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}

class TOPMOD_OT_insert_edge(bpy.types.Operator):
    bl_idname = "mesh.topmod_insert_edge"
    bl_label = "Insert Edge"
    bl_description = "This operator inserts edges between selected corners in viewport."
    bl_options = {"REGISTER"}

    v1: bpy.props.IntProperty(name = "v1", description = "Index of first vertex",default=-1)
    v2: bpy.props.IntProperty(name = "v2", description = "Index of second vertex",default=-1)
    f1: bpy.props.IntProperty(name = "f1", description = "Index of first face",default=-1)
    f2: bpy.props.IntProperty(name = "f2", description = "Index of second face",default=-1)
    
    from bmesh.types import BMVert, BMFace, BMesh
    
    @classmethod  
    def poll(cls, context):
        if (context.active_object is None):
            return False
        return context.active_object.mode == 'EDIT'

    def execute(self, context):
        from pytopmod.core.dlfl import operators
        mesh, bm, verts, faces = bpyToDLFL()
        operators.insert_edge(mesh,verts[self.v1], faces[self.f1] , verts[self.v2], faces[self.f2])

        mesh = DLFLtoBPY(mesh)
        bpy.ops.object.editmode_toggle()
        context.object.data = mesh
        bpy.ops.object.editmode_toggle()
        bpy.ops.mesh.select_all(action='DESELECT')
        return {'FINISHED'}

    def modal(self, context, event):
        self.invoked = True
        if self.v1 != -1 and self.v2 != -1 and self.f1 != -1 and self.f2 != -1:
            return self.execute(context)
        if not event.alt:
            if event.type in {'ONE', 'TWO', 'THREE', 'MOUSEMOVE', 'LEFTMOUSE','RIGHTMOUSE','WHEELDOWNMOUSE','MIDDLEMOUSE', 'WHEELUPMOUSE'}:
                return {'PASS_THROUGH'}
        if event.alt and event.type == 'ONE':  # Apply
            self.v1 = [v for v in bmesh.from_edit_mesh(context.object.data).verts if v.select][0].index
            return {'PASS_THROUGH'}
        elif event.alt and event.type == 'TWO':  # Apply
            self.f1 = [f for f in bmesh.from_edit_mesh(context.object.data).faces if f.select][0].index
            return {'PASS_THROUGH'}
        elif event.alt and event.type == 'THREE':  # Apply
            self.v2 = [v for v in bmesh.from_edit_mesh(context.object.data).verts if v.select][0].index
            return {'PASS_THROUGH'}
        elif event.alt and event.type == 'FOUR':  # Apply
            self.f2 = [f for f in bmesh.from_edit_mesh(context.object.data).faces if f.select][0].index
            return {'PASS_THROUGH'}
        elif event.type == 'ESC':
            return {'CANCELLED'}
        else:
            return {'PASS_THROUGH'}
        
        return {'RUNNING_MODAL'}

    def invoke(self, context, event):
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}

class TOPMOD_PT_panel(bpy.types.Panel):
    bl_label = "TopMod Panel"
    bl_category = "TopMod"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"

    def draw(self, context):
        layout = self.layout

        for dependency in dependencies:
            if dependency.name is None and hasattr(globals()[dependency.module], "__version__"):
                layout.label(text=f"pytopmod module has been installed and imported")
            elif 'pytopmod' in sys.modules:
                layout.label(text=f"pytopmod module has been installed and imported")
            else:
                layout.label(text=f"{dependency.module}")
                
        layout.label(text="Subdivision Operations")
        layout.operator(TOPMOD_OT_triangular_subdivision.bl_idname)
        
        layout.label(text="Topology Changing Operations")
        layout.operator(TOPMOD_OT_delete_edge.bl_idname)
        layout.operator(TOPMOD_OT_insert_edge.bl_idname)

        layout.label(text="To insert/delete edges you need to define the following:")
        layout.label(text="v1: select a vertex in edit mode and press ALT+1")
        layout.label(text="f1: select a face in edit mode and press ALT+2")
        layout.label(text="v2: select a vertex in edit mode and press ALT+3")
        layout.label(text="f2: select a face in edit mode and press ALT+4")
        
      

class TOPMOD_MT_PIE_delete_selection(bpy.types.Menu):
    # label is displayed at the center of the pie menu.
    bl_label = "TopMod Delete Set Operations"

    def draw(self, context):
        layout = self.layout

        pie = layout.menu_pie()
        pie.operator("mesh.triangular_subdivision", text="Subdivide", icon='MESH_PLANE')
        pie.operator("mesh.topmod_delete_edge", text="Delete Edge", icon='MESH_TORUS')



class TOPMOD_MT_PIE(bpy.types.Menu):
    bl_label = "TopMod Operations"

    def draw(self, context):
        layout = self.layout

        pie = layout.menu_pie()
        column = pie.split().column()
        column.operator("mesh.triangular_subdivision", text="Subdivide", icon='MESH_PLANE')
        column.operator("mesh.topmod_delete_edge", text="Delete Edge", icon='MESH_TORUS')

classes = (TOPMOD_OT_triangular_subdivision,
           TOPMOD_OT_delete_edge,
           TOPMOD_OT_insert_edge,
           TOPMOD_PT_panel,
           TOPMOD_MT_PIE,
           TOPMOD_MT_PIE_delete_selection)


class TOPMOD_PT_warning_panel(bpy.types.Panel):
    bl_label = "TopMod Package Warning"
    bl_category = "TopMod"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"

    @classmethod
    def poll(self, context):
        return not dependencies_installed

    def draw(self, context):
        layout = self.layout

        lines = [f"Please install the missing dependencies for the \"{bl_info.get('name')}\" add-on.",
                 f"1. Open the preferences (Edit > Preferences > Add-ons).",
                 f"2. Search for the \"{bl_info.get('name')}\" add-on.",
                 f"3. Open the details section of the add-on.",
                 f"4. Click on the \"{TOPMOD_OT_install_dependencies.bl_label}\" button.",
                 f"   This will download and install the missing Python packages, if Blender has the required",
                 f"   permissions.",
                 f"If you're attempting to run the add-on from the text editor, you won't see the options described",
                 f"above. Please install the add-on properly through the preferences.",
                 f"1. Open the add-on preferences (Edit > Preferences > Add-ons).",
                 f"2. Press the \"Install\" button.",
                 f"3. Search for the add-on file.",
                 f"4. Confirm the selection by pressing the \"Install Add-on\" button in the file browser."]

        for line in lines:
            layout.label(text=line)


class TOPMOD_OT_install_dependencies(bpy.types.Operator):
    bl_idname = "topmod.install_dependencies"
    bl_label = "Install Dependencies"
    bl_description = ("Downloads and installs the required python packages for topmod add-on. "
                      "Internet connection is required. Blender may have to be started with "
                      "elevated permissions in order to install the package")
    bl_options = {"REGISTER", "INTERNAL"}

    @classmethod
    def poll(self, context):
        # Deactivate when dependencies have been installed
        return not dependencies_installed

    def execute(self, context):
        try:
            install_pip()
            for dependency in dependencies:
                pull_and_import_module('https://github.com/topmod-org/pytopmod-core.git',module_name=dependency.module,
                                          package_name=dependency.package,
                                          global_name=dependency.name)
        except (subprocess.CalledProcessError, ImportError) as err:
            self.report({"ERROR"}, str(err))
            return {"CANCELLED"}

        global dependencies_installed
        dependencies_installed = True

        # Register the panels, operators, etc. since dependencies are installed
        for cls in classes:
            bpy.utils.register_class(cls)

        return {"FINISHED"}

class TOPMOD_preferences(bpy.types.AddonPreferences):
    bl_idname = __name__

    def draw(self, context):
        layout = self.layout
        layout.operator(TOPMOD_OT_install_dependencies.bl_idname, icon="CONSOLE")
        if 'pytopmod' not in sys.modules:
            layout.label(text="After installing dependencies Blender needs to be restarted to activate add-on")


preference_classes = (TOPMOD_PT_warning_panel,
                      TOPMOD_OT_install_dependencies,
                      TOPMOD_preferences)

addon_keymaps = []

def register():
    global dependencies_installed
    dependencies_installed = False

    for cls in preference_classes:
        bpy.utils.register_class(cls)

    try:
        for dependency in dependencies:
            import_module(module_name=dependency.module, global_name=dependency.name)
        dependencies_installed = True
    except ModuleNotFoundError:
        # Don't register other panels, operators etc.
        return

    for cls in classes:
        bpy.utils.register_class(cls)
        
    wm = bpy.context.window_manager
    km = wm.keyconfigs.addon.keymaps.new(name='Object Non-modal')

    kmi = km.keymap_items.new('wm.call_menu_pie', 'T', 'PRESS', shift=True)
    kmi.properties.name = 'TOPMOD_MT_PIE'        

    addon_keymaps.append(km)


def unregister():
    for cls in preference_classes:
        bpy.utils.unregister_class(cls)

    if dependencies_installed:
        for cls in classes:
            bpy.utils.unregister_class(cls)
            
    wm = bpy.context.window_manager
    for km in addon_keymaps:
        for kmi in km.keymap_items:
            km.keymap_items.remove(kmi)

        wm.keyconfigs.addon.keymaps.remove(km)

    # clear the list
    del addon_keymaps[:]
            
if __name__ == "__main__":
    register()


