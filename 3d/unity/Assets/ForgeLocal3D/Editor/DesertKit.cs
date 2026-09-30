using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEngine;
using Object=UnityEngine.Object;

namespace ForgeLocal3D
{
    // Lot 266, en mode batch : ajoute au kit du désert les seuls modules choisis par Python
    // (sorties/kit/selection.json, écrit d'après kit.NOUVEAUX), puis mesure leurs prefabs. Aucune
    // scène ouverte, aucun autre prefab refait, aucun matériau recréé. Il ne juge rien :
    // local3d/desert/kit.py lit unity-kit.json et décide.
    public static class DesertKit
    {
        const string Output="../local3d/desert/sorties/kit/";

        [Serializable] class Selection{public string[] modules;}
        [Serializable] public class Module
        {
            public string id="";public int niveaux=-1;public int[] triangles=new int[0];
            // Point le plus bas des maillages du LOD0, prefab posé à l'origine ; -1 : non mesuré.
            public double y_min=-1;public string[] materiaux=new string[0];
        }
        [Serializable] public class Rapport
        {
            public string status="mesure",unity="";public Module[] modules=new Module[0];
            public string[] materiaux_manquants=new string[0],erreurs=new string[0];
        }

        [MenuItem("Forge/Désert/Kit : ajouter les nouveaux modules")]
        public static void Start()
        {
            var modules=new List<Module>();var manquants=new List<string>();var erreurs=new List<string>();
            try
            {
                var selection=JsonUtility.FromJson<Selection>(File.ReadAllText(Output+"selection.json"));
                if(selection?.modules==null||selection.modules.Length==0)
                    throw new InvalidOperationException("Aucun module : lancer py local3d/atelier_desert.py kit");
                AssetDatabase.Refresh(ImportAssetOptions.ForceSynchronousImport);
                var catalog=JsonUtility.FromJson<VillageV2Builder.Catalog>(File.ReadAllText(DesertBuilder.Root+"/Data/catalogue.json"));
                // Les matériaux existants, chargés tels quels : un absent se note, il n'est pas recréé.
                var materials=new Dictionary<string,Material>();
                foreach(var matter in catalog.materials)
                {
                    var m=AssetDatabase.LoadAssetAtPath<Material>(DesertBuilder.Root+"/Materials/"+matter.name+".mat");
                    if(m)materials[matter.name]=m;else manquants.Add(matter.name);
                }
                foreach(string id in selection.modules)
                {
                    var asset=catalog.assets.FirstOrDefault(a=>a.id==id);
                    if(asset==null){erreurs.Add(id+" : absent du catalogue");continue;}
                    try{modules.Add(Measure(VillageV2Builder.ImportPrefab(DesertBuilder.Root,asset,materials)));}
                    catch(Exception e){erreurs.Add(id+" : "+e.Message);}
                }
                AssetDatabase.SaveAssets();
            }
            catch(Exception e){erreurs.Add(e.Message);}
            var rapport=new Rapport{unity=Application.unityVersion,modules=modules.ToArray(),materiaux_manquants=manquants.ToArray(),erreurs=erreurs.ToArray()};
            File.WriteAllText(Path.GetFullPath(Output+"unity-kit.json"),JsonUtility.ToJson(rapport,true));
            Debug.Log("FORGE_DESERT_KIT modules="+modules.Count+" erreurs="+erreurs.Count+" materiaux_manquants="+manquants.Count);
        }

        static Module Measure(GameObject prefab)
        {
            var go=(GameObject)PrefabUtility.InstantiatePrefab(prefab);
            try
            {
                go.transform.SetPositionAndRotation(Vector3.zero,Quaternion.identity);go.transform.localScale=Vector3.one;
                var result=new Module{id=prefab.name};
                var group=go.GetComponent<LODGroup>();
                if(!group)return result;
                var lods=group.GetLODs();result.niveaux=lods.Length;
                MeshFilter[] Filters(LOD lod)=>lod.renderers.Where(r=>r).Select(r=>r.GetComponent<MeshFilter>()).Where(f=>f&&f.sharedMesh).ToArray();
                result.triangles=lods.Select(l=>Filters(l).Sum(f=>f.sharedMesh.triangles.Length/3)).ToArray();
                if(lods.Length>0)
                {
                    var points=Filters(lods[0]).SelectMany(f=>f.sharedMesh.vertices.Select(v=>f.transform.localToWorldMatrix.MultiplyPoint3x4(v))).ToArray();
                    if(points.Length>0)result.y_min=points.Min(p=>p.y);
                }
                result.materiaux=go.GetComponentsInChildren<Renderer>(true).SelectMany(r=>r.sharedMaterials).Select(m=>m?m.name:"(vide)").Distinct().OrderBy(n=>n,StringComparer.Ordinal).ToArray();
                return result;
            }
            finally{Object.DestroyImmediate(go);}
        }
    }
}
