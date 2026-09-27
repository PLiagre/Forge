using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEngine;

namespace ForgeLocal3D
{
    public static class CitadelHabitatBuilder
    {
        const string Root=CitadelBuilder.Root;
        [Serializable] class ModuleSpec { public string id,label,kind; public float[] size; }
        [Serializable] class Piece { public string asset; public float[] position; public float rotation; }
        [Serializable] class House { public string id; public Piece[] pieces; }
        [Serializable] class Catalog { public float grille,etage; public ModuleSpec[] modules; public House[] maisons; }
        static Vector3 P(float[] v)=>new Vector3(-v[0],v[2],-v[1]);
        public static void Prepare(Dictionary<string,GameObject> prefabs)
        {
            var spec=JsonUtility.FromJson<Catalog>(File.ReadAllText(Root+"/Data/habitat.json"));
            if(spec.modules.Length==0||spec.maisons.Length==0)throw new InvalidOperationException("Kit d'habitat vide");
            Directory.CreateDirectory(Root+"/Prefabs/Habitat/Pieces");AssetDatabase.Refresh();
            var pieces=new Dictionary<string,GameObject>();var adapted=new Dictionary<Material,Material>();
            foreach(string id in spec.modules.Select(m=>m.id).Concat(spec.maisons.Select(m=>m.id)))
            {
                string path=AssetDatabase.GetAssetPath(prefabs[id]);var root=PrefabUtility.LoadPrefabContents(path);
                foreach(var r in root.GetComponentsInChildren<MeshRenderer>(true))
                    r.sharedMaterials=r.sharedMaterials.Select(m=>
                    {if(!adapted.TryGetValue(m,out var a))adapted[m]=a=CitadelArchitecture.Adapt(m);return a;}).ToArray();
                prefabs[id]=PrefabUtility.SaveAsPrefabAsset(root,path);PrefabUtility.UnloadPrefabContents(root);
            }
            // Les pièces proches réutilisent les mêmes maillages. Les maisons conservent
            // un seul groupe de détail et deux versions fusionnées pour la distance.
            foreach(var module in spec.modules)
            {
                var source=prefabs[module.id].GetComponent<LODGroup>().GetLODs()[0].renderers.Single();
                var piece=new GameObject(module.id);
                piece.AddComponent<MeshFilter>().sharedMesh=source.GetComponent<MeshFilter>().sharedMesh;
                piece.AddComponent<MeshRenderer>().sharedMaterials=source.sharedMaterials;
                pieces[module.id]=PrefabUtility.SaveAsPrefabAsset(piece,Root+"/Prefabs/Habitat/Pieces/"+module.id+".prefab");
                UnityEngine.Object.DestroyImmediate(piece);
            }
            foreach(var house in spec.maisons)
            {
                string path=AssetDatabase.GetAssetPath(prefabs[house.id]);var root=PrefabUtility.LoadPrefabContents(path);
                var lod=root.GetComponent<LODGroup>();var levels=lod.GetLODs();
                foreach(var old in levels[0].renderers)UnityEngine.Object.DestroyImmediate(old.gameObject);
                var near=new List<Renderer>();
                foreach(var p in house.pieces)
                {
                    var go=(GameObject)PrefabUtility.InstantiatePrefab(pieces[p.asset],root.transform);
                    go.transform.localPosition=P(p.position);go.transform.localRotation=Quaternion.Euler(0,-p.rotation,0);
                    near.Add(go.GetComponent<Renderer>());
                }
                levels[0]=new LOD(.18f,near.ToArray());levels[1].screenRelativeTransitionHeight=.065f;
                lod.SetLODs(levels);lod.RecalculateBounds();
                prefabs[house.id]=PrefabUtility.SaveAsPrefabAsset(root,path);PrefabUtility.UnloadPrefabContents(root);
            }
            string kitPath=Root+"/Prefabs/Habitat/Kit_Habitat.asset";
            var kit=AssetDatabase.LoadAssetAtPath<CitadelHabitatKit>(kitPath);
            if(!kit){kit=ScriptableObject.CreateInstance<CitadelHabitatKit>();AssetDatabase.CreateAsset(kit,kitPath);}
            kit.grid=spec.grille;kit.storey=spec.etage;
            string gridPath=Root+"/Prefabs/Habitat/Grille.mat";
            kit.gridMaterial=AssetDatabase.LoadAssetAtPath<Material>(gridPath);
            if(!kit.gridMaterial){kit.gridMaterial=new Material(Shader.Find("Universal Render Pipeline/Unlit"));AssetDatabase.CreateAsset(kit.gridMaterial,gridPath);}
            kit.gridMaterial.color=new Color(.52f,.66f,.67f);EditorUtility.SetDirty(kit.gridMaterial);
            kit.modules=spec.modules.Select(m=>new CitadelHabitatKit.Module{id=m.id,label=m.label,kind=m.kind,prefab=prefabs[m.id],size=new Vector3(m.size[0],m.size[2],m.size[1])}).ToArray();
            kit.houses=spec.maisons.Select(h=>prefabs[h.id]).ToArray();EditorUtility.SetDirty(kit);
            AssetDatabase.SaveAssets();
        }
        public static void Configure(Camera view,CitadelTraversal walk)
        {
            var build=new GameObject("Construction des habitations").AddComponent<CitadelConstruction>();
            build.kit=AssetDatabase.LoadAssetAtPath<CitadelHabitatKit>(Root+"/Prefabs/Habitat/Kit_Habitat.asset");
            build.view=view;build.walk=walk;
            var env=UnityEngine.Object.FindFirstObjectByType<CitadelEnvironment>();
            var house=GameObject.Find("Architecture").GetComponentsInChildren<LODGroup>()
                .Where(g=>g.name.StartsWith("maison_modulaire_")&&g.transform.position.y>35)
                .OrderBy(g=>Mathf.Abs(g.transform.position.x+23)+Mathf.Abs(g.transform.position.z-25)).First();
            Vector3 target=house.transform.position+Vector3.up*6;
            env.viewpoints=env.viewpoints.Concat(new[]{new CitadelEnvironment.Viewpoint{name="Habitat",target=target,
                position=target+new Vector3(9,10,8),fieldOfView=60},new CitadelEnvironment.Viewpoint{name="Chantier",target=walk.plots[0].position+Vector3.up*5,
                position=walk.plots[0].position+new Vector3(-16,20,30),fieldOfView=42}}).ToArray();
        }
        [Serializable] class Report { public string status="valide";public int modules,maisons,pieces_partagees;public bool contre_epreuve_module; }
        public static void Verify(string output)
        {
            var build=UnityEngine.Object.FindFirstObjectByType<CitadelConstruction>();
            var houses=GameObject.Find("Architecture").GetComponentsInChildren<LODGroup>().Where(g=>g.name.StartsWith("maison_modulaire_")).ToArray();
            var spec=JsonUtility.FromJson<Catalog>(File.ReadAllText(Root+"/Data/habitat.json"));
            int Check()
            {
                if(!build||!build.kit||houses.Length==0)throw new InvalidOperationException("Habitat ou chantier absent");
                int count=0;
                foreach(var house in houses)
                {
                    var recipe=spec.maisons.Single(h=>house.name.StartsWith(h.id+"__"));
                    var children=house.GetLODs()[0].renderers;
                    if(children.Length!=recipe.pieces.Length)throw new InvalidOperationException("Composition incomplète");
                    for(int i=0;i<children.Length;i++)
                    {
                        var p=recipe.pieces[i];var module=build.kit.modules.Single(m=>m.id==p.asset);
                        var original=module.prefab.GetComponent<LODGroup>().GetLODs()[0].renderers.Single().GetComponent<MeshFilter>().sharedMesh;
                        if(children[i].GetComponent<MeshFilter>().sharedMesh!=original||
                           (children[i].transform.localPosition-P(p.position)).magnitude>.001f||
                           Quaternion.Angle(children[i].transform.localRotation,Quaternion.Euler(0,-p.rotation,0))>.001f)
                            throw new InvalidOperationException("Pièce non partagée ou raccord déplacé : "+p.asset);
                        count++;
                    }
                }
                return count;
            }
            int count=Check();var sample=houses[0].GetLODs()[0].renderers[0].transform;Vector3 position=sample.localPosition;
            sample.localPosition+=Vector3.right;bool red=false;
            try{Check();}catch(InvalidOperationException){red=true;}finally{sample.localPosition=position;}
            if(!red)throw new InvalidOperationException("Un module déplacé passe le contrôle");
            File.WriteAllText(output,JsonUtility.ToJson(new Report{modules=build.kit.modules.Length,maisons=houses.Length,pieces_partagees=count,contre_epreuve_module=red},true));
        }
    }
}
