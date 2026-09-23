using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEngine;
using UnityEngine.Rendering;

namespace ForgeLocal3D
{
    // Adaptation artistique du pack HDRP au paysage maillé de la citadelle.
    // Les originaux restent intacts ; les matériaux et prefabs adaptés sont partagés.
    public static class CitadelTerrainSample
    {
        static string Pack=>AssetDatabase.IsValidFolder("Assets/Vendor/TerrainDemoScene_HDRP")
            ?"Assets/Vendor/TerrainDemoScene_HDRP/":"Assets/TerrainDemoScene_HDRP/";
        const string Materials=CitadelBuilder.Root+"/Materials/Tiers/TerrainSample/";
        const string Prefabs=CitadelBuilder.Root+"/Prefabs/TerrainSample/";
        const string Group="Terrain Sample ”” végétation et affleurements";
        static readonly string[] Layers={"Cliff_Mossy_E","Grass_Soil_A","Pebbles_B"};
        static readonly string[] Slots={"Rock","Soil","Gravel"};
        static readonly Dictionary<string,Material> adapted=new();
        static readonly List<Kind> kinds=new();
        sealed class Kind { public GameObject prefab;public Bounds bounds;public bool rock; }
        [Serializable] public class Report
        {
            public string status="valide",scene,pack=Pack;
            public int surfaces=-1,vegetation=-1,rochers=-1,triangles_decor=-1,collisions_rochers=-1;
            public int arbres_remplaces=-1,rochers_parois=-1;
            public bool contre_epreuve_foret;
            public bool contre_epreuve_materiau,contre_epreuve_acces;
        }
        static bool Present=>AssetDatabase.IsValidFolder(Pack.TrimEnd('/'));
        static bool Surface(Renderer r)=>r.name.StartsWith("Terrain_vallee")||r.name.StartsWith("falaise_")||r.name.StartsWith("montagne_")||r.name.StartsWith("Socle_terrasses");
        static T Load<T>(string path) where T:UnityEngine.Object
        {
            var asset=AssetDatabase.LoadAssetAtPath<T>(Pack+path);
            if(!asset)throw new InvalidOperationException("Asset Terrain Sample absent : "+path);
            return asset;
        }
        static Material Material(string name,string shader)
        {
            string path=Materials+name+".mat";
            var m=AssetDatabase.LoadAssetAtPath<Material>(path);
            var s=Shader.Find(shader);if(!s)throw new InvalidOperationException("Shader absent : "+shader);
            if(!m){m=new Material(s);AssetDatabase.CreateAsset(m,path);}
            m.shader=s;m.shaderKeywords=Array.Empty<string>();m.enableInstancing=true;
            return m;
        }
        public static void Apply(VillageV2Builder.SceneSpec spec,CitadelTraversal walk)
        {
            adapted.Clear();kinds.Clear();
            if(!Present){Debug.LogWarning("Terrain Sample absent : paysage d'origine conservé.");return;}
            Directory.CreateDirectory(Materials);Directory.CreateDirectory(Prefabs);AssetDatabase.Refresh();
            CitadelForest.Apply(Pack,spec);
            SmoothRelief();
            var layers=Layers.Select(n=>Load<TerrainLayer>("Terrain/Layers/"+n+".terrainlayer")).ToArray();
            foreach(var r in UnityEngine.Object.FindObjectsByType<MeshRenderer>(FindObjectsSortMode.None).Where(Surface))
            {
                r.sharedMaterials=r.sharedMaterials.Select(source=>
                {
                    // La neige géométrique des corniches et des falaises reste blanche.
                    bool valley=r.name.StartsWith("Terrain_vallee");
                    if(source.name.StartsWith("neige")&&!valley)return source;
                    string key=(valley?"Sol_":"Relief_")+source.name;
                    if(adapted.TryGetValue(key,out var known))return known;
                    var m=Material(key,"Forge/CitadelTerrain");m.SetTexture("_BaseMap",source.GetTexture("_BaseMap"));
                    for(int i=0;i<layers.Length;i++)
                    {
                        if(!layers[i].diffuseTexture||!layers[i].normalMapTexture||!layers[i].maskMapTexture)
                            throw new InvalidOperationException("Couche Terrain Sample incomplète : "+layers[i].name);
                        m.SetTexture("_"+Slots[i]+"Map",layers[i].diffuseTexture);
                        m.SetTexture("_"+Slots[i]+"Normal",layers[i].normalMapTexture);
                        m.SetTexture("_"+Slots[i]+"Mask",layers[i].maskMapTexture);
                    }
                    m.SetFloat("_Valley",valley?1:0);
                    m.SetFloat("_SnowCover",.76f);m.SetFloat("_RockScale",5.5f);m.SetFloat("_SoilScale",5);m.SetFloat("_GravelScale",3);
                    m.SetColor("_RockTint",new Color(.60f,.64f,.67f));
                    EditorUtility.SetDirty(m);return adapted[key]=m;
                }).ToArray();
            }
            foreach(string name in new[]{"GrassDry_A","GrassDry_B","GrassDry_C","Bush_Twig","BushDry_B"})
                kinds.Add(Prepare(name,false));
            foreach(string name in new[]{"Rock_A_01","Rock_B_01","Rock_C_01"})kinds.Add(Prepare(name,true));
            var root=new GameObject(Group).transform;
            var terrain=GameObject.Find("Relief, eau et ouvrages").GetComponentsInChildren<MeshCollider>().Single(c=>c.name.StartsWith("Terrain_vallee"));
            var rng=new System.Random(spec.seed+7319);
            float R(float a,float b)=>a+(float)rng.NextDouble()*(b-a);
            Physics.SyncTransforms();
            // Touffes espacées en petits groupes le long des accès, puis quelques îlots de lande.
            foreach(var route in walk.routes)
            for(int s=1;s<route.points.Length;s++)
            {
                var a=route.points[s-1];var b=route.points[s];var direction=b-a;direction.y=0;
                float length=direction.magnitude;if(length<.1f)continue;direction/=length;
                for(float d=R(0,2.8f);d<length;d+=2.8f)
                for(int side=-1;side<=1;side+=2)
                {
                    var p=Vector3.Lerp(a,b,d/length)+new Vector3(direction.z,0,-direction.x)*side*(route.width/2+R(2,8));
                    Place(kinds[rng.Next(5)],p,R(.4f,1.1f),R(0,360),root,walk,terrain);
                }
            }
            for(int i=0;i<950;i++)
            {
                var p=new Vector3(R(-270,270),0,R(-230,180));
                bool rock=i%5==0;
                var kind=rock?kinds[5+rng.Next(3)]:kinds[rng.Next(5)];
                Place(kind,p,rock?R(.9f,3.3f):R(.4f,1.2f),R(0,360),root,walk,terrain);
            }
            Debug.Log("CITADELLE_TERRAIN_SAMPLE "+spec.id+" objets="+root.childCount);
        }

        static void SmoothRelief()
        {
            string folder=CitadelBuilder.Root+"/Meshes/Relief/";Directory.CreateDirectory(folder);AssetDatabase.Refresh();
            var cache=new Dictionary<Mesh,Mesh>();
            foreach(var filter in UnityEngine.Object.FindObjectsByType<MeshFilter>(FindObjectsSortMode.None)
                .Where(f=>f.name.StartsWith("montagne_")||f.name.StartsWith("falaise_")||f.name.StartsWith("Socle_terrasses")))
            {
                var source=filter.sharedMesh;if(!source)continue;
                if(!cache.TryGetValue(source,out var mesh))
                {
                    AssetDatabase.TryGetGUIDAndLocalFileIdentifier(source,out string guid,out long id);
                    string path=folder+guid+"_"+id+".asset";
                    var copy=UnityEngine.Object.Instantiate(source);copy.name=source.name;
                    var vertices=copy.vertices;var normals=copy.normals;var sums=new Dictionary<Vector3Int,Vector3>();
                    Vector3Int Key(Vector3 v)=>Vector3Int.RoundToInt(v*1000);
                    for(int v=0;v<vertices.Length;v++){var key=Key(vertices[v]);sums[key]=sums.GetValueOrDefault(key)+normals[v];}
                    float blend=filter.name.StartsWith("montagne_")?.85f:.55f;
                    for(int v=0;v<vertices.Length;v++)normals[v]=Vector3.Slerp(normals[v],sums[Key(vertices[v])].normalized,blend).normalized;
                    copy.normals=normals;
                    mesh=AssetDatabase.LoadAssetAtPath<Mesh>(path);
                    if(mesh){EditorUtility.CopySerialized(copy,mesh);UnityEngine.Object.DestroyImmediate(copy);}
                    else{mesh=copy;AssetDatabase.CreateAsset(mesh,path);}
                    cache[source]=mesh;
                }
                filter.sharedMesh=mesh;
            }
        }

        // Les propriétés sérialisées restent lisibles sans installer le shader HDRP d'origine.
        internal static Texture SavedTexture(Material source,params string[] names)
        {
            var entries=new SerializedObject(source).FindProperty("m_SavedProperties.m_TexEnvs");
            foreach(string name in names)
            for(int i=0;i<entries.arraySize;i++)
            {
                var e=entries.GetArrayElementAtIndex(i);
                if(e.FindPropertyRelative("first").stringValue==name)
                {
                    var t=e.FindPropertyRelative("second.m_Texture").objectReferenceValue as Texture;
                    if(t)return t;
                }
            }
            throw new InvalidOperationException("Texture source absente : "+source.name+" / "+string.Join(",",names));
        }
        static Material Convert(Material source,bool rock)
        {
            string key="Objet_"+source.name;
            if(adapted.TryGetValue(key,out var known))return known;
            var m=Material(key,"Forge/CitadelLit");
            m.SetTexture("_BaseMap",SavedTexture(source,"_BaseColorMap","Texture2D_E1B0D043"));
            m.SetTexture("_BumpMap",SavedTexture(source,"_NormalMap","Texture2D_9DCAAA49"));
            m.SetTexture("_MaskMap",SavedTexture(source,"_MaskMap","Texture2D_A5E0646"));
            m.SetFloat("_HasMaskMap",1);m.SetFloat("_HasGlossMap",0);m.SetFloat("_Metallic",0);
            m.SetFloat("_Smoothness",.32f);m.SetFloat("_BumpScale",.55f);m.SetFloat("_SnowFactor",rock?.8f:.22f);
            m.SetFloat("_SnowBase",.65f);m.SetFloat("_Weathering",.06f);m.SetFloat("_Wind",rock?0:.18f);m.SetFloat("_WindHeight",1);
            m.SetFloat("_AlphaClip",rock?0:1);m.SetFloat("_Cutoff",.38f);
            m.SetColor("_BaseColor",rock?new Color(.77f,.81f,.85f):new Color(.7f,.68f,.61f));
            m.SetColor("_EmissionColor",Color.black);
            m.renderQueue=(int)(rock?RenderQueue.Geometry:RenderQueue.AlphaTest);
            m.SetOverrideTag("RenderType",rock?"Opaque":"TransparentCutout");
            m.SetColor("_RockTint",new Color(.60f,.64f,.67f));
                    EditorUtility.SetDirty(m);return adapted[key]=m;
        }
        static Kind Prepare(string name,bool rock)
        {
            var source=Load<GameObject>("Prefabs/"+(rock?"Rocks/":"Details/")+name+".prefab");
            var probe=(GameObject)PrefabUtility.InstantiatePrefab(source);
            probe.transform.SetPositionAndRotation(Vector3.zero,Quaternion.identity);probe.transform.localScale=Vector3.one;
            var go=new GameObject(name);
            try
            {
                // Les petits rochers emploient le niveau intermédiaire du pack : pas cinq maillages superposés.
                var all=probe.GetComponentsInChildren<MeshRenderer>(true);
                var selected=rock?all.Where(r=>r.name.EndsWith("_LOD02")).ToArray():all;
                if(selected.Length==0)throw new InvalidOperationException("Maillage du pack absent : "+name);
                foreach(var r in selected)
                {
                    var f=r.GetComponent<MeshFilter>();if(!f||!f.sharedMesh)throw new InvalidOperationException("Maillage absent : "+r.name);
                    var child=new GameObject(r.name);child.transform.SetParent(go.transform);
                    child.transform.SetPositionAndRotation(r.transform.position,r.transform.rotation);child.transform.localScale=r.transform.lossyScale;
                    child.AddComponent<MeshFilter>().sharedMesh=f.sharedMesh;
                    var renderer=child.AddComponent<MeshRenderer>();renderer.sharedMaterials=r.sharedMaterials.Select(m=>Convert(m,rock)).ToArray();
                    renderer.shadowCastingMode=rock?ShadowCastingMode.On:ShadowCastingMode.Off;
                    if(rock)child.AddComponent<MeshCollider>().sharedMesh=f.sharedMesh;
                }
                var renderers=go.GetComponentsInChildren<Renderer>();var bounds=renderers[0].bounds;
                foreach(var r in renderers.Skip(1))bounds.Encapsulate(r.bounds);
                if(bounds.size.y<.001f)throw new InvalidOperationException("Objet sans hauteur : "+name);
                var prefab=PrefabUtility.SaveAsPrefabAsset(go,Prefabs+name+".prefab");
                return new Kind{prefab=prefab,bounds=bounds,rock=rock};
            }
            finally{UnityEngine.Object.DestroyImmediate(probe);UnityEngine.Object.DestroyImmediate(go);}
        }
        static float Flat(Vector3 v)=>new Vector2(v.x,v.z).magnitude;
        static bool Reserved(Vector3 p,float radius,CitadelTraversal walk)
        {
            if(Flat(p-walk.spawn)<14+radius||Flat(p-walk.forest)<12+radius)return true;
            if(walk.plots.Any(plot=>Mathf.Abs(p.x-plot.position.x)<plot.size.x/2+radius+2&&Mathf.Abs(p.z-plot.position.z)<plot.size.y/2+radius+2))return true;
            foreach(var route in walk.routes)for(int i=1;i<route.points.Length;i++)
            {
                Vector2 a=new(route.points[i-1].x,route.points[i-1].z),b=new(route.points[i].x,route.points[i].z),q=new(p.x,p.z);
                var ab=b-a;float t=ab.sqrMagnitude<1e-6f?0:Mathf.Clamp01(Vector2.Dot(q-a,ab)/ab.sqrMagnitude);
                if(Vector2.Distance(q,a+ab*t)<route.width/2+radius+1)return true;
            }
            return false;
        }
        static bool Place(Kind kind,Vector3 p,float height,float yaw,Transform root,CitadelTraversal walk,MeshCollider terrain)
        {
            float scale=height/kind.bounds.size.y;
            float radius=new Vector2(kind.bounds.extents.x,kind.bounds.extents.z).magnitude*scale;
            if(Reserved(p,radius,walk))return false;
            if(!Physics.Raycast(new Vector3(p.x,900,p.z),Vector3.down,out var hit,1800)||hit.collider!=terrain||hit.normal.y<.8f)return false;
            // L'emprise entière repose sur le terrain ; les bâtiments, troncs et accessoires l'excluent.
            float low=hit.point.y,high=low;
            foreach(var offset in new[]{Vector3.right,Vector3.left,Vector3.forward,Vector3.back})
            {
                var q=p+offset*radius*.8f;
                if(!Physics.Raycast(new Vector3(q.x,900,q.z),Vector3.down,out var edge,1800)||edge.collider!=terrain)return false;
                low=Mathf.Min(low,edge.point.y);high=Mathf.Max(high,edge.point.y);
            }
            if(high-low>(kind.rock?height*.32f:.22f))return false;
            var center=new Vector3(p.x,low+height*.5f,p.z);
            if(Physics.OverlapBox(center,new Vector3(radius,height*.45f,radius)).Any(c=>c!=terrain))return false;
            var go=(GameObject)PrefabUtility.InstantiatePrefab(kind.prefab);go.transform.SetParent(root);
            go.name=(kind.rock?"Affleurement_":"Lande_")+root.childCount.ToString("D4")+"_"+kind.prefab.name;
            var rotation=Quaternion.Euler(0,yaw,0);
            var bottom=kind.bounds.center-new Vector3(0,kind.bounds.extents.y,0);
            go.transform.localScale=Vector3.one*scale;
            go.transform.SetPositionAndRotation(new Vector3(p.x,low-(kind.rock?height*.32f:.035f),p.z)-rotation*(bottom*scale),rotation);
            Physics.SyncTransforms();return true;
        }
        static Report Inspect(string scene)
        {
            var report=new Report{scene=scene};if(!Present)return report;
            var surfaces=UnityEngine.Object.FindObjectsByType<MeshRenderer>(FindObjectsSortMode.None).Where(Surface).ToArray();
            if(surfaces.Length==0)throw new InvalidOperationException("Aucune surface de terrain à contrôler");
            foreach(var r in surfaces)
            foreach(var m in r.sharedMaterials.Where(m=>!m||!m.name.StartsWith("neige")))
            {
                if(!m||m.shader.name!="Forge/CitadelTerrain"||!m.GetTexture("_BaseMap"))throw new InvalidOperationException("Terrain non adapté : "+r.name);
                foreach(string slot in Slots)foreach(string suffix in new[]{"Map","Normal","Mask"})
                    if(!m.GetTexture("_"+slot+suffix))throw new InvalidOperationException("Couche absente : "+slot+suffix);
            }
            var root=GameObject.Find(Group);if(!root)throw new InvalidOperationException("Décor Terrain Sample absent");
            var walk=UnityEngine.Object.FindFirstObjectByType<CitadelTraversal>();if(!walk)throw new InvalidOperationException("Parcours absent");
            var objects=root.transform.Cast<Transform>().ToArray();
            report.surfaces=surfaces.Length;report.vegetation=objects.Count(t=>t.name.StartsWith("Lande_"));report.rochers=objects.Length-report.vegetation;
            if(report.vegetation==0||report.rochers==0)throw new InvalidOperationException("Échantillon Terrain Sample vide");
            foreach(var t in objects)
            {
                var renderers=t.GetComponentsInChildren<MeshRenderer>();if(renderers.Length==0)throw new InvalidOperationException("Décor sans rendu");
                var bounds=renderers[0].bounds;foreach(var r in renderers.Skip(1))bounds.Encapsulate(r.bounds);
                // L'emprise circulaire est calculée avant rotation, comme lors du placement.
                var prefab=PrefabUtility.GetCorrespondingObjectFromSource(t.gameObject);
                var local=new Bounds();bool first=true;
                foreach(var f in prefab.GetComponentsInChildren<MeshFilter>())
                {
                    var b=f.sharedMesh.bounds;
                    for(int x=-1;x<=1;x+=2)for(int y=-1;y<=1;y+=2)for(int z=-1;z<=1;z+=2)
                    {
                        var p=f.transform.TransformPoint(b.center+Vector3.Scale(b.extents,new Vector3(x,y,z)));
                        if(first){local=new Bounds(p,Vector3.zero);first=false;}else local.Encapsulate(p);
                    }
                }
                float radius=new Vector2(local.extents.x,local.extents.z).magnitude*t.localScale.x;
                if(Reserved(bounds.center,radius,walk))throw new InvalidOperationException("Décor dans un accès : "+t.name);
                foreach(var r in renderers)foreach(var m in r.sharedMaterials)
                    if(!m||m.shader.name!="Forge/CitadelLit"||!m.GetTexture("_BaseMap")||!m.GetTexture("_BumpMap")||!m.GetTexture("_MaskMap")||ShaderUtil.ShaderHasError(m.shader))
                        throw new InvalidOperationException("Matériau du décor incomplet : "+t.name);
                if(t.name.StartsWith("Affleurement_")&&t.GetComponentsInChildren<MeshCollider>().Length==0)
                    throw new InvalidOperationException("Rocher sans collision : "+t.name);
            }
            report.triangles_decor=root.GetComponentsInChildren<MeshFilter>().Sum(f=>f.sharedMesh.triangles.Length/3);
            report.collisions_rochers=root.GetComponentsInChildren<MeshCollider>().Length;
            if(ShaderUtil.ShaderHasError(surfaces[0].sharedMaterial.shader))throw new InvalidOperationException("Shader du terrain en erreur");
            return report;
        }
        public static void Verify(VillageV2Builder.SceneSpec spec,string output)
        {
            string scene=spec.id;
            var report=Inspect(scene);
            if(Present)
            {
                report.arbres_remplaces=CitadelForest.Verify(spec);
                report.contre_epreuve_foret=CitadelForest.Countercheck(spec);
                report.rochers_parois=CitadelDecor.CliffRocks;
                var surface=UnityEngine.Object.FindObjectsByType<MeshRenderer>(FindObjectsSortMode.None).First(Surface);
                var materials=surface.sharedMaterials;
                try
                {
                    surface.sharedMaterial=null;
                    try{Inspect(scene);}catch(InvalidOperationException e){report.contre_epreuve_materiau=e.Message.StartsWith("Terrain non adapté");}
                }
                finally{surface.sharedMaterials=materials;}
                var plant=GameObject.Find(Group).transform.GetChild(0);var position=plant.position;
                try
                {
                    plant.position=UnityEngine.Object.FindFirstObjectByType<CitadelTraversal>().spawn;
                    try{Inspect(scene);}catch(InvalidOperationException e){report.contre_epreuve_acces=e.Message.StartsWith("Décor dans un accès");}
                }
                finally{plant.position=position;}
                if(!report.contre_epreuve_materiau||!report.contre_epreuve_acces)throw new InvalidOperationException("Contrôle Terrain Sample insensible à sa contre-épreuve");
                Inspect(scene);
            }
            File.WriteAllText(output,JsonUtility.ToJson(report,true));
            Debug.Log("TERRAIN_SAMPLE_VERIFIE "+scene+" surfaces="+report.surfaces+" végétation="+report.vegetation+" rochers="+report.rochers);
        }
        public static void CaptureDetails(Camera camera,string output)
        {
            if(!Present)return;
            var root=GameObject.Find(Group);var walk=UnityEngine.Object.FindFirstObjectByType<CitadelTraversal>();
            var forge=GameObject.Find("forge");
            if(forge)
            {
                var point=UnityEngine.Object.FindFirstObjectByType<CitadelEnvironment>().viewpoints.Single(p=>p.name=="Forge");
                camera.transform.position=point.position;camera.transform.LookAt(point.target);camera.fieldOfView=point.fieldOfView;
                CitadelPlayCheck.Capture(camera,output+"unity_forge.png",1600,900);
            }
            foreach(var shot in new[]{("Lande_","lande"),("Affleurement_","roche")})
            {
                var subject=root.transform.Cast<Transform>().Where(t=>t.name.StartsWith(shot.Item1))
                    .OrderBy(t=>Flat(t.position-walk.forest)).First();
                var bounds=subject.GetComponentInChildren<Renderer>().bounds;
                var position=bounds.center+new Vector3(5,2.5f,6);
                if(Physics.Raycast(new Vector3(position.x,900,position.z),Vector3.down,out var ground,1800))
                    position.y=Mathf.Max(position.y,ground.point.y+1.8f);
                camera.transform.position=position;camera.transform.LookAt(bounds.center+Vector3.up*.4f);camera.fieldOfView=48;
                CitadelPlayCheck.Capture(camera,output+"unity_"+shot.Item2+".png",1600,900);
            }
        }
    }
}
