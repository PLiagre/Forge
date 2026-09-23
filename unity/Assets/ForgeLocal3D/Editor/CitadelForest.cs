using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEngine;

namespace ForgeLocal3D
{
    // Les arbres du manifeste gardent leur identité, leur pied et leur abattage.
    // Seule leur couronne de rendu est remplacée par les conifères du pack.
    public static class CitadelForest
    {
        const string Folder=CitadelBuilder.Root+"/Prefabs/TerrainSample/Foret/";
        const string Materials=CitadelBuilder.Root+"/Materials/Tiers/TerrainSample/";
        const string Visual="Conifère Terrain Sample";
        static readonly Dictionary<string,Material> materials=new();
        sealed class Species { public GameObject prefab;public float height;public int levels; }
        public static void Apply(string pack,VillageV2Builder.SceneSpec spec)
        {
            Directory.CreateDirectory(Folder);AssetDatabase.Refresh();materials.Clear();
            var species=new[]{"Conifer/Conifer","Pines/Pine_A/Pine_A","Pines/Pine_B/Pine_B","Pines/Pine_D/Pine_D"}
                .Select(path=>Prepare(pack+"Prefabs/Trees/"+path+".prefab")).ToArray();
            var trees=UnityEngine.Object.FindObjectsByType<CitadelTree>(FindObjectsSortMode.None).OrderBy(t=>t.name).ToArray();
            var rng=new System.Random(spec.seed+4801);
            foreach(var tree in trees)
            {
                var lod=tree.GetComponent<LODGroup>();var old=lod.GetLODs()[0].renderers;
                var bounds=old[0].bounds;foreach(var r in old.Skip(1))bounds.Encapsulate(r.bounds);
                var type=species[rng.NextDouble()<.6?0:rng.Next(1,species.Length)];
                // Une cime plus pleine ; la variation de hauteur suit celle du manifeste.
                float height=bounds.size.y*(.92f+(float)rng.NextDouble()*.28f);
                foreach(var r in tree.GetComponentsInChildren<Renderer>())r.gameObject.SetActive(false);
                var crown=(GameObject)PrefabUtility.InstantiatePrefab(type.prefab,tree.transform);crown.name=Visual;
                crown.transform.localPosition=Vector3.zero;crown.transform.localRotation=Quaternion.identity;
                crown.transform.localScale=new Vector3(1.24f,1,1.24f)*(height/type.height/tree.transform.lossyScale.y);
                var levels=Enumerable.Range(0,type.levels).Select(i=>new LOD(new[]{.32f,.14f,.024f}[i],
                    crown.transform.Find("Niveau_"+i).GetComponentsInChildren<Renderer>())).ToArray();
                lod.SetLODs(levels);lod.fadeMode=LODFadeMode.None;lod.RecalculateBounds();
            }
            if(trees.Length==0)throw new InvalidOperationException("Aucun arbre à remplacer");
            Debug.Log("CITADELLE_FORET "+spec.id+" arbres="+trees.Length+" essences="+species.Length);
        }
        static Species Prepare(string path)
        {
            var source=AssetDatabase.LoadAssetAtPath<GameObject>(path);
            if(!source)throw new InvalidOperationException("Conifère absent : "+path);
            var probe=(GameObject)PrefabUtility.InstantiatePrefab(source);var visual=new GameObject(source.name);
            try
            {
                probe.transform.SetPositionAndRotation(Vector3.zero,Quaternion.identity);probe.transform.localScale=Vector3.one;
                var group=probe.GetComponent<LODGroup>();if(!group)throw new InvalidOperationException("Conifère sans niveaux de détail : "+path);
                var lods=group.GetLODs();int count=Math.Min(3,lods.Length);
                var bounds=lods[0].renderers[0].bounds;foreach(var r in lods[0].renderers.Skip(1))bounds.Encapsulate(r.bounds);
                if(bounds.size.y<1||count<3)throw new InvalidOperationException("Conifère incomplet : "+path);
                for(int i=0;i<count;i++)
                {
                    var level=new GameObject("Niveau_"+i).transform;level.SetParent(visual.transform,false);
                    foreach(var renderer in lods[i].renderers)
                    {
                        var filter=renderer.GetComponent<MeshFilter>();
                        if(!filter||!filter.sharedMesh)throw new InvalidOperationException("Maillage d'arbre absent : "+renderer.name);
                        var child=new GameObject(renderer.name);child.transform.SetParent(level,false);
                        child.transform.SetPositionAndRotation(renderer.transform.position-Vector3.up*bounds.min.y,renderer.transform.rotation);
                        child.transform.localScale=renderer.transform.lossyScale;
                        child.AddComponent<MeshFilter>().sharedMesh=filter.sharedMesh;
                        child.AddComponent<MeshRenderer>().sharedMaterials=renderer.sharedMaterials.Select(m=>Convert(m,bounds.size.y)).ToArray();
                    }
                }
                var prefab=PrefabUtility.SaveAsPrefabAsset(visual,Folder+source.name+".prefab");
                Debug.Log("CONIFERE_SOURCE "+source.name+" hauteur="+bounds.size.y+" triangles="+string.Join(",",lods.Take(count).Select(l=>l.renderers.Sum(r=>r.GetComponent<MeshFilter>().sharedMesh.triangles.Length/3))));
                return new Species{prefab=prefab,height=bounds.size.y,levels=count};
            }
            finally{UnityEngine.Object.DestroyImmediate(probe);UnityEngine.Object.DestroyImmediate(visual);}
        }
        static Texture Map(Material source,string name)
        {
            var entries=new SerializedObject(source).FindProperty("m_SavedProperties.m_TexEnvs");
            for(int i=0;i<entries.arraySize;i++)
            {
                var item=entries.GetArrayElementAtIndex(i);
                if(item.FindPropertyRelative("first").stringValue==name)
                {
                    var texture=item.FindPropertyRelative("second.m_Texture").objectReferenceValue as Texture;
                    if(texture)return texture;
                }
            }
            throw new InvalidOperationException("Carte d'arbre absente : "+source.name+" / "+name);
        }
        static Material Convert(Material source,float height)
        {
            if(materials.TryGetValue(source.name,out var known))return known;
            string path=Materials+"Foret_"+source.name+".mat";
            var m=AssetDatabase.LoadAssetAtPath<Material>(path);var shader=Shader.Find("Forge/CitadelLit");
            if(!m){m=new Material(shader);AssetDatabase.CreateAsset(m,path);}m.shader=shader;
            bool bark=source.name.Contains("Bark")||source.name.Contains("Cap");
            m.SetTexture("_BaseMap",Map(source,"_MainTex"));m.SetTexture("_BumpMap",Map(source,"_BumpMap"));m.SetTexture("_MaskMap",Map(source,"_ExtraTex"));
            m.SetFloat("_HasMaskMap",1);m.SetFloat("_SpeedTreeMask",1);m.SetFloat("_HasGlossMap",0);m.SetFloat("_Metallic",0);
            m.SetFloat("_BumpScale",.65f);m.SetFloat("_Smoothness",.28f);m.SetFloat("_SnowBase",1);m.SetFloat("_SnowFactor",bark?.36f:1.25f);
            m.SetFloat("_AlphaClip",bark?0:1);m.SetFloat("_Cutoff",.28f);m.SetFloat("_Wind",.45f);m.SetFloat("_WindHeight",height);
            m.SetFloat("_Foliage",bark?0:1);m.SetFloat("_Weathering",0);m.SetColor("_EmissionColor",Color.black);
            m.SetColor("_BaseColor",bark?new Color(.82f,.78f,.73f):new Color(.62f,.72f,.67f));
            m.renderQueue=bark?2000:2450;m.SetOverrideTag("RenderType",bark?"Opaque":"TransparentCutout");m.enableInstancing=true;
            EditorUtility.SetDirty(m);return materials[source.name]=m;
        }
        public static int Verify(VillageV2Builder.SceneSpec spec)
        {
            var expected=spec.instances.Where(i=>i.asset.StartsWith("sapin_")).Select(i=>i.id).OrderBy(n=>n).ToArray();
            var trees=UnityEngine.Object.FindObjectsByType<CitadelTree>(FindObjectsSortMode.None).OrderBy(t=>t.name).ToArray();
            if(expected.Length==0||!trees.Select(t=>t.name).SequenceEqual(expected))throw new InvalidOperationException("Identités de la forêt divergentes");
            foreach(var tree in trees)
            {
                var crown=tree.transform.Find(Visual);var collider=tree.GetComponent<CapsuleCollider>();var lod=tree.GetComponent<LODGroup>();
                if(!crown||!crown.gameObject.activeSelf||!collider||!collider.enabled||!lod)throw new InvalidOperationException("Arbre incomplet : "+tree.name);
                foreach(var level in lod.GetLODs())
                    if(level.renderers.Length==0||level.renderers.Any(r=>!r||!r.transform.IsChildOf(crown)||!r.gameObject.activeInHierarchy))
                        throw new InvalidOperationException("Niveau de forêt absent : "+tree.name);
                foreach(var m in crown.GetComponentsInChildren<Renderer>().SelectMany(r=>r.sharedMaterials))
                    if(!m||!m.GetTexture("_BaseMap")||!m.GetTexture("_MaskMap")||m.GetFloat("_SpeedTreeMask")!=1||ShaderUtil.ShaderHasError(m.shader))
                        throw new InvalidOperationException("Matériau de forêt incorrect : "+tree.name);
            }
            return trees.Length;
        }
        public static bool Countercheck(VillageV2Builder.SceneSpec spec)
        {
            var crown=UnityEngine.Object.FindFirstObjectByType<CitadelTree>().transform.Find(Visual);
            bool rejected=false;
            try{crown.gameObject.SetActive(false);try{Verify(spec);}catch(InvalidOperationException e){rejected=e.Message.StartsWith("Arbre incomplet");}}
            finally{crown.gameObject.SetActive(true);}
            Verify(spec);if(!rejected)throw new InvalidOperationException("Contrôle insensible à une forêt masquée");return true;
        }
    }
}
