using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.SceneManagement;
using Object=UnityEngine.Object;

namespace ForgeLocal3D
{
    // Lot 266, en mode batch : ajoute au kit du désert les seuls modules choisis par Python
    // (sorties/kit/selection.json, écrit d'après kit.NOUVEAUX), puis mesure leurs prefabs. Aucune
    // scène ouverte, aucun autre prefab refait, aucun matériau recréé. Lot 269 : les
    // références de la sélection (bâtiments finis des chantiers) sont mesurées sur leur prefab
    // existant, en lecture seule. Lot 270 : après les mesures, il photographie les étapes de chantier
    // (rangées `planche` de la sélection) dans une scène neuve jamais enregistrée. Il ne juge rien :
    // local3d/desert/kit.py lit unity-kit.json et la planche, et décide.
    public static class DesertKit
    {
        const string Output="../local3d/desert/sorties/kit/";
        // Chemin de la planche relatif au dossier du désert : kit.PLANCHE_UNITY.
        const string PlancheChemin="sorties/diagnostic/kit_chantiers_unity.png";
        const int CaseLargeur=640,CaseHauteur=480;
        static readonly Color32 Fond=new Color32(150,166,184,255);
        // La façade regarde +Z (le -Y de Blender) : trois quarts depuis la façade, un peu en surplomb.
        static readonly Vector3 Vue=new Vector3(-.6f,.5f,1f).normalized;

        [Serializable] class Rangee{public string fini;public string[] etapes;}
        [Serializable] class Selection{public string[] modules;public string[] references;public Rangee[] planche;}
        [Serializable] public class Case
        {
            public string id="";public int rangee=-1,colonne=-1;
            // Rectangle en pixels de l'image PNG, origine en haut à gauche.
            public int x=-1,y=-1,largeur=-1,hauteur=-1;
            // Renderers actifs du LOD0 au moment du rendu ; -1 : non mesuré.
            public int renderers=-1;
        }
        [Serializable] public class PlancheRapport
        {
            public string chemin="";public int largeur=-1,hauteur=-1;public int[] fond=new int[0];
            // Scène active au moment du rendu : vide si elle n'a jamais été enregistrée ; -1 : non relevée.
            public string scene_chemin="-1";public Case[] cases=new Case[0];
        }
        [Serializable] public class Module
        {
            public string id="";public int niveaux=-1;public int[] triangles=new int[0];
            // Point le plus bas des maillages du LOD0, prefab posé à l'origine ; -1 : non mesuré.
            public double y_min=-1;public string[] materiaux=new string[0];
            // Lot 269 : l'enveloppe des maillages du LOD0 dans le repère d'Unity ; -1 : non mesuré.
            public double x_min=-1,x_max=-1,z_min=-1,z_max=-1,y_max=-1;
        }
        [Serializable] public class Rapport
        {
            public string status="mesure",unity="";public Module[] modules=new Module[0];
            // Lot 269 : les bâtiments finis des chantiers, mesurés sur leur prefab existant.
            public Module[] references=new Module[0];
            public string[] materiaux_manquants=new string[0],erreurs=new string[0];
            public PlancheRapport planche=new PlancheRapport();
        }

        [MenuItem("Forge/Désert/Kit : ajouter les nouveaux modules")]
        public static void Start()
        {
            var modules=new List<Module>();var references=new List<Module>();var manquants=new List<string>();var erreurs=new List<string>();
            Selection selection=null;
            try
            {
                selection=JsonUtility.FromJson<Selection>(File.ReadAllText(Output+"selection.json"));
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
                // Les bâtiments finis de référence : leur prefab existant est chargé et mesuré,
                // jamais recréé ni enregistré.
                foreach(string id in selection.references??new string[0])
                {
                    var prefab=AssetDatabase.LoadAssetAtPath<GameObject>(DesertBuilder.Root+"/Prefabs/"+id+".prefab");
                    if(!prefab){erreurs.Add(id+" : prefab de référence absent");continue;}
                    try{references.Add(Measure(prefab));}
                    catch(Exception e){erreurs.Add(id+" : "+e.Message);}
                }
            }
            catch(Exception e){erreurs.Add(e.Message);}
            var planche=Planche(selection?.planche,erreurs);
            var rapport=new Rapport{unity=Application.unityVersion,modules=modules.ToArray(),references=references.ToArray(),materiaux_manquants=manquants.ToArray(),erreurs=erreurs.ToArray(),planche=planche};
            File.WriteAllText(Path.GetFullPath(Output+"unity-kit.json"),JsonUtility.ToJson(rapport,true));
            Debug.Log("FORGE_DESERT_KIT modules="+modules.Count+" references="+references.Count+" erreurs="+erreurs.Count+" materiaux_manquants="+manquants.Count+" cases="+planche.cases.Length);
        }

        // Lot 270 : une case par prefab de chaque rangée (étapes puis bâtiment fini), rendue seule,
        // LOD0 forcé, dans une scène neuve jamais enregistrée : une lumière, une caméra au fond uni,
        // pas de sol. Le cadrage d'une rangée est calé sur l'enveloppe du bâtiment fini, pour que ses
        // étapes se comparent à la même échelle. Les cases s'assemblent en une image : une rangée par
        // chantier, une colonne par étape.
        static PlancheRapport Planche(Rangee[] rangees,List<string> erreurs)
        {
            var planche=new PlancheRapport{fond=new int[]{Fond.r,Fond.g,Fond.b}};
            if(rangees==null||rangees.Length==0){erreurs.Add("planche : aucune rangée dans la sélection");return planche;}
            // Dans l'éditeur ouvert (menu), la scène neuve remplacerait les scènes ouvertes : elles sont rouvertes après.
            if(!Application.isBatchMode&&!EditorSceneManager.SaveCurrentModifiedScenesIfUserWantsTo()){erreurs.Add("planche : scènes ouvertes non enregistrées");return planche;}
            var ouvertes=EditorSceneManager.GetSceneManagerSetup();
            var dossier=Path.Combine(Path.GetTempPath(),"forge_planche_"+Guid.NewGuid().ToString("N"));
            Texture2D image=null;
            try
            {
                Directory.CreateDirectory(dossier);
                EditorSceneManager.NewScene(NewSceneSetup.EmptyScene,NewSceneMode.Single);
                RenderSettings.skybox=null;RenderSettings.fog=false;
                RenderSettings.ambientMode=AmbientMode.Flat;RenderSettings.ambientLight=new Color(.45f,.45f,.48f);DynamicGI.UpdateEnvironment();
                var soleil=new GameObject("Soleil").AddComponent<Light>();
                soleil.type=LightType.Directional;soleil.intensity=1.3f;soleil.shadows=LightShadows.Soft;
                soleil.transform.rotation=Quaternion.LookRotation(new Vector3(.45f,-.75f,-.5f));
                var camera=new GameObject("Camera").AddComponent<Camera>();
                camera.clearFlags=CameraClearFlags.SolidColor;camera.backgroundColor=Fond;camera.fieldOfView=30;camera.aspect=(float)CaseLargeur/CaseHauteur;

                var instances=new Dictionary<string,GameObject>();
                foreach(var id in rangees.SelectMany(r=>r.etapes??new string[0]).Distinct())
                {
                    var prefab=AssetDatabase.LoadAssetAtPath<GameObject>(DesertBuilder.Root+"/Prefabs/"+id+".prefab");
                    if(!prefab){erreurs.Add("planche : prefab absent : "+id);continue;}
                    var go=(GameObject)PrefabUtility.InstantiatePrefab(prefab);
                    go.transform.SetPositionAndRotation(Vector3.zero,Quaternion.identity);go.SetActive(false);instances[id]=go;
                }
                int colonnes=rangees.Max(r=>r.etapes?.Length??0);
                planche.largeur=colonnes*CaseLargeur;planche.hauteur=rangees.Length*CaseHauteur;
                image=new Texture2D(planche.largeur,planche.hauteur,TextureFormat.RGB24,false);
                image.SetPixels32(Enumerable.Repeat(Fond,planche.largeur*planche.hauteur).ToArray());
                var cases=new List<Case>();
                for(int r=0;r<rangees.Length;r++)
                {
                    var rangee=rangees[r];
                    if(rangee.fini==null||!instances.TryGetValue(rangee.fini,out var fini)){erreurs.Add("planche : bâtiment fini absent : "+rangee.fini);continue;}
                    var enveloppe=Montrer(fini);fini.SetActive(false);
                    if(enveloppe==null){erreurs.Add("planche : "+rangee.fini+" n'a aucun renderer au LOD0");continue;}
                    var b=enveloppe.Value;float rayon=b.extents.magnitude,distance=rayon/Mathf.Sin(camera.fieldOfView*.5f*Mathf.Deg2Rad)*1.05f;
                    camera.transform.position=b.center+Vue*distance;camera.transform.LookAt(b.center);
                    camera.nearClipPlane=Mathf.Max(.05f,distance-rayon*1.5f);camera.farClipPlane=distance+rayon*1.5f;
                    var etapes=rangee.etapes??new string[0];
                    for(int c=0;c<etapes.Length;c++)
                    {
                        var id=etapes[c];
                        if(!instances.TryGetValue(id,out var go))continue;
                        Montrer(go);
                        int actifs=Lod0(go).Count(x=>x.enabled&&x.gameObject.activeInHierarchy);
                        planche.scene_chemin=SceneManager.GetActiveScene().path;
                        var pixels=CitadelPlayCheck.Capture(camera,Path.Combine(dossier,id+".png"),CaseLargeur,CaseHauteur);
                        go.SetActive(false);
                        // La texture compte ses lignes depuis le bas, le PNG depuis le haut.
                        int x=c*CaseLargeur,y=r*CaseHauteur;
                        image.SetPixels32(x,planche.hauteur-y-CaseHauteur,CaseLargeur,CaseHauteur,pixels);
                        cases.Add(new Case{id=id,rangee=r,colonne=c,x=x,y=y,largeur=CaseLargeur,hauteur=CaseHauteur,renderers=actifs});
                    }
                }
                image.Apply();
                var chemin=Path.GetFullPath("../local3d/desert/"+PlancheChemin);
                Directory.CreateDirectory(Path.GetDirectoryName(chemin));File.WriteAllBytes(chemin,image.EncodeToPNG());
                planche.chemin=PlancheChemin;planche.cases=cases.ToArray();
                foreach(var go in instances.Values)Object.DestroyImmediate(go);
            }
            catch(Exception e){erreurs.Add("planche : "+e.Message);}
            finally
            {
                if(image)Object.DestroyImmediate(image);
                if(Directory.Exists(dossier))Directory.Delete(dossier,true);
                if(!Application.isBatchMode&&ouvertes.Length>0&&ouvertes.All(s=>!string.IsNullOrEmpty(s.path)))EditorSceneManager.RestoreSceneManagerSetup(ouvertes);
            }
            return planche;
        }

        // Active une instance, LOD0 forcé, et rend l'enveloppe de son LOD0 ; null s'il n'a aucun renderer.
        static Bounds? Montrer(GameObject go)
        {
            go.SetActive(true);
            var group=go.GetComponent<LODGroup>();if(group)group.ForceLOD(0);
            var lod=Lod0(go);if(lod.Length==0)return null;
            var b=lod[0].bounds;foreach(var x in lod)b.Encapsulate(x.bounds);
            return b;
        }

        static Renderer[] Lod0(GameObject go)
        {
            var group=go.GetComponent<LODGroup>();
            return group&&group.lodCount>0?group.GetLODs()[0].renderers.Where(r=>r).ToArray():go.GetComponentsInChildren<Renderer>(true);
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
                    if(points.Length>0)
                    {
                        result.y_min=points.Min(p=>p.y);result.y_max=points.Max(p=>p.y);
                        result.x_min=points.Min(p=>p.x);result.x_max=points.Max(p=>p.x);
                        result.z_min=points.Min(p=>p.z);result.z_max=points.Max(p=>p.z);
                    }
                }
                result.materiaux=go.GetComponentsInChildren<Renderer>(true).SelectMany(r=>r.sharedMaterials).Select(m=>m?m.name:"(vide)").Distinct().OrderBy(n=>n,StringComparer.Ordinal).ToArray();
                return result;
            }
            finally{Object.DestroyImmediate(go);}
        }
    }
}
