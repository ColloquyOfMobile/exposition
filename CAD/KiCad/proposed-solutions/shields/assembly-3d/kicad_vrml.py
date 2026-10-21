"""Import KiCad's tessellated VRML visual export, retaining its materials.

Run in Blender with -- manifest.json. Uses the original visual models rather
than substituting uncoloured STEP compounds. Coordinates use PCB underside Z=0.
Only the node types emitted by KiCad's VRML exporter are accepted.
"""
from pathlib import Path
import json
import math
import re
import sys


class Reader:
    arities={'center':3,'rotation':4,'scale':3,'scaleOrientation':4,'translation':3,
             'diffuseColor':3,'specularColor':3,'emissiveColor':3}
    scalars={'ambientIntensity','shininess','transparency','normalPerVertex','solid',
             'ccw','convex','creaseAngle','colorPerVertex'}
    arrays={'children','point','coordIndex','vector','normalIndex','colorIndex'}
    nodes={'appearance','material','geometry','coord','normal','color'}
    kinds={'Transform','Shape','Appearance','Material','IndexedFaceSet','Coordinate','Normal'}

    def __init__(self,text):
        text=re.sub(r'#[^\n]*','',text)
        self.tokens=re.findall(r'[A-Za-z_][\w.\-]*|[-+]?(?:\d*\.\d+|\d+\.?\d*)(?:[eE][-+]?\d+)?|[{}\[\]]',text)
        self.pos=0;self.definitions={}

    def take(self,expected=None):
        value=self.tokens[self.pos];self.pos+=1
        if expected is not None and value!=expected:raise ValueError((expected,value,self.pos))
        return value

    def number(self):
        token=self.take()
        if token in ('TRUE','FALSE'):
            return token == 'TRUE'
        return float(token)

    def node(self):
        kind=self.take();name=None
        if kind=='USE':return self.definitions[self.take()]
        if kind=='DEF':name=self.take();kind=self.take()
        if kind not in self.kinds:raise ValueError('Unsupported KiCad VRML node: '+kind)
        self.take('{');result={'kind':kind}
        if name:self.definitions[name]=result
        while self.tokens[self.pos]!='}':
            key=self.take()
            if key in self.arities:result[key]=[self.number() for _ in range(self.arities[key])]
            elif key in self.scalars:result[key]=self.number()
            elif key in self.nodes:result[key]=self.node()
            elif key in self.arrays:
                self.take('[');values=[]
                while self.tokens[self.pos]!=']':values.append(self.node() if key=='children' else self.number())
                self.take(']');result[key]=values
            else:raise ValueError('Unsupported KiCad VRML field: '+key)
        self.take('}');return result

    def read(self):
        nodes=[]
        while self.pos<len(self.tokens):nodes.append(self.node())
        return nodes


def convert(entry):
    import bpy
    from mathutils import Matrix,Vector
    bpy.ops.wm.read_factory_settings(use_empty=True)
    nodes=Reader(Path(entry['vrml']).read_text()).read()
    assert len(nodes)==1 and nodes[0]['kind']=='Transform'
    materials={};counts={'models':0,'board_meshes':0,'vertices':0,'faces':0}

    def rotation(values):
        x,y,z,angle=values
        return Matrix.Rotation(angle,4,Vector((x,y,z))) if abs(angle)>1e-12 else Matrix.Identity(4)

    def transform(node):
        translation=Matrix.Translation(Vector(node.get('translation',(0,0,0))))
        center=Matrix.Translation(Vector(node.get('center',(0,0,0))))
        orient=rotation(node.get('scaleOrientation',(0,0,1,0)))
        scale=Matrix.Diagonal((*node.get('scale',(1,1,1)),1))
        return translation@center@rotation(node.get('rotation',(0,0,1,0)))@orient@scale@orient.inverted()@center.inverted()

    def material(node):
        data=node.get('appearance',{}).get('material',{})
        color=tuple(data.get('diffuseColor',(.8,.8,.8)))
        alpha=1-float(data.get('transparency',0));key=(color,alpha,float(data.get('shininess',.2)))
        if key not in materials:
            item=bpy.data.materials.new('KiCad visual '+str(len(materials)+1))
            item.diffuse_color=(*color,alpha);item.use_nodes=True
            shader=item.node_tree.nodes.get('Principled BSDF')
            shader.inputs['Base Color'].default_value=(*color,alpha)
            shader.inputs['Alpha'].default_value=alpha
            shader.inputs['Roughness'].default_value=max(.12,1-math.sqrt(key[2]))
            if alpha<1:item.surface_render_method='DITHERED'
            materials[key]=item
        return materials[key]

    def collect(node,matrix,vertices,faces,colors,normals):
        if node['kind']=='Transform':
            for child in node.get('children',[]):collect(child,matrix@transform(node),vertices,faces,colors,normals)
        elif node['kind']=='Shape':
            geometry=node['geometry'];assert geometry['kind']=='IndexedFaceSet'
            coords=geometry['coord']['point'];offset=len(vertices)
            vertices.extend(tuple((matrix@Vector(coords[i:i+3]))*.001) for i in range(0,len(coords),3))
            raw_normals=geometry.get('normal',{}).get('vector',[])
            normal_matrix=matrix.to_3x3().inverted().transposed()
            if len(raw_normals)==len(coords):
                normals.extend(tuple((normal_matrix@Vector(raw_normals[i:i+3])).normalized()) for i in range(0,len(raw_normals),3))
            else:normals.extend([(0,0,0)]*(len(coords)//3))
            current=[];mat=material(node)
            for number in geometry['coordIndex']:
                number=int(number)
                if number==-1:
                    if len(current)>=3:
                        faces.append(tuple(offset+n for n in current));colors.append(mat)
                    current=[]
                else:current.append(number)
            counts['vertices']+=len(coords)//3
        else:raise ValueError(node['kind'])

    global_matrix=Matrix.Translation((0,0,entry['thickness_mm']/2))@transform(nodes[0])
    model_names=entry['model_order'];board_index=0
    assert len(nodes[0].get('children',[]))>=len(model_names)
    for index,child in enumerate(nodes[0].get('children',[])):
        if index<len(model_names):
            assert child['kind']=='Transform'
            name=model_names[index]['ref'];counts['models']+=1
        else:
            board_index+=1;name=entry['name']+'_visual_layers_'+str(board_index);counts['board_meshes']+=1
        vertices=[];faces=[];colors=[];normals=[]
        collect(child,global_matrix,vertices,faces,colors,normals)
        if not faces:continue
        mesh=bpy.data.meshes.new(name);mesh.from_pydata(vertices,[],faces);mesh.update()
        unique=list(dict.fromkeys(colors))
        for mat in unique:mesh.materials.append(mat)
        indices={mat:i for i,mat in enumerate(unique)}
        for face,mat in zip(mesh.polygons,colors):face.material_index=indices[mat];face.use_smooth=True
        mesh.normals_split_custom_set_from_vertices(normals)
        obj=bpy.data.objects.new(name,mesh);bpy.context.scene.collection.objects.link(obj)
        counts['faces']+=len(faces)
    assert counts['models']==len(model_names),'VRML omitted a model'
    counts['materials']=len(materials)
    bpy.ops.export_scene.gltf(filepath=entry['output'],export_format='GLB',export_apply=False,
                             export_cameras=False,export_lights=False,export_extras=True)
    return counts


if __name__=='__main__':
    path=Path(sys.argv[sys.argv.index('--')+1]);entries=json.loads(path.read_text())
    report={entry['name']:convert(entry) for entry in entries}
    path.with_suffix('.results.json').write_text(json.dumps(report,indent=2)+'\n')
    print('KiCad visual conversion complete',report,flush=True)
