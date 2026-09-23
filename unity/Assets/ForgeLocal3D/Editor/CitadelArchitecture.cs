using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEngine;

namespace ForgeLocal3D
{
    // Les façades partagent la vraie texture pierre/bois de Blacksmith.
    // Un rectangle de l'atlas se répète avec les UV métriques des bâtiments.
    public static class CitadelArchitecture
    {
        const string Pack="Assets/Vendor/3DForge/FantasyExteriors/Village & Towns/Textures/";
        const string Folder=CitadelBuilder.Root+"/Materials/Tiers/Architecture/";
        static readonly string[] Stones={"enduit","basalte","pierre_taille","calcaire"};
        public static void Verify()
        {
            var root=GameObject.Find("Architecture");
            if(!root)throw new InvalidOperationException("Architecture absente");
            var materials=root.GetComponentsInChildren<MeshRenderer>(true).SelectMany(r=>r.sharedMaterials).Distinct().ToArray();
            if(materials.Any(m=>Stones.Contains(m.name)||m.name.StartsWith("bois_")))
                throw new InvalidOperationException("Ancienne façade encore présente");
            var stone=materials.Where(m=>m.name.StartsWith("Citadelle_citadelle_")).ToArray();
            if(stone.Length!=2||stone.Any(m=>!m.GetTexture("_BaseMap")||!m.GetTexture("_BumpMap")||m.GetFloat("_UseAtlas")!=0||ShaderUtil.ShaderHasError(m.shader)))
                throw new InvalidOperationException("Pierre claire de la fortification incomplète");
            var adapted=materials.Where(m=>m.name.StartsWith("Blacksmith_")).ToArray();
            if(adapted.Length==0)throw new InvalidOperationException("Aucun matériau Blacksmith adapté");
            foreach(var m in adapted)
                if(m.GetFloat("_UseAtlas")!=1||!m.GetTexture("_BaseMap")||!m.GetTexture("_BumpMap")||ShaderUtil.ShaderHasError(m.shader))
                    throw new InvalidOperationException("Texture Blacksmith incomplète : "+m.name);
        }
        public static Material Adapt(Material original,bool fortification=false)
        {
            if(fortification && new[]{"basalte","pierre_taille","calcaire"}.Contains(original.name))
            {
                string surface=original.name=="calcaire"?"citadelle_moulure":"citadelle_pierre";
                string stonePath=Folder+"Citadelle_"+surface+".mat";
                Directory.CreateDirectory(Folder);
                var stone=AssetDatabase.LoadAssetAtPath<Material>(stonePath);
                if(!stone){stone=new Material(Shader.Find("Forge/CitadelLit"));AssetDatabase.CreateAsset(stone,stonePath);}
                stone.SetTexture("_BaseMap",AssetDatabase.LoadAssetAtPath<Texture2D>(CitadelBuilder.Root+"/Textures/"+surface+"_BaseColor.png"));
                stone.SetTexture("_BumpMap",AssetDatabase.LoadAssetAtPath<Texture2D>(CitadelBuilder.Root+"/Textures/"+surface+"_Normal.png"));
                stone.SetFloat("_UseAtlas",0);stone.SetTextureScale("_BaseMap",Vector2.one);
                stone.SetColor("_BaseColor",Color.white);stone.SetFloat("_BumpScale",.30f);
                stone.SetFloat("_Smoothness",.12f);stone.SetFloat("_Weathering",.035f);
                stone.SetFloat("_SnowBase",.6f);stone.SetFloat("_SnowFactor",.13f);
                stone.enableInstancing=true;EditorUtility.SetDirty(stone);return stone;
            }
            string name=original.name;bool wood=name.StartsWith("bois_");
            bool plaster=name=="habitat_enduit",brick=name=="habitat_brique";
            if(!wood&&!plaster&&!brick&&!Stones.Contains(name))return original;
            Directory.CreateDirectory(Folder);
            string path=Folder+"Blacksmith_"+name+".mat";
            var m=AssetDatabase.LoadAssetAtPath<Material>(path);
            if(!m){m=new Material(Shader.Find("Forge/CitadelLit"));AssetDatabase.CreateAsset(m,path);}
            var color=AssetDatabase.LoadAssetAtPath<Texture2D>(Pack+"fe_village_base.png");
            var normal=AssetDatabase.LoadAssetAtPath<Texture2D>(Pack+"fe_village_base_NRM.png");
            if(!color||!normal)throw new InvalidOperationException("Textures Blacksmith absentes");
            m.SetTexture("_BaseMap",color);m.SetTexture("_BumpMap",normal);m.SetFloat("_UseAtlas",1);
            // Rectangles mesurés dans l'atlas, origine en bas à gauche.
            m.SetVector("_AtlasRect",wood?new Vector4(.215f,.503f,.198f,.239f):
                plaster?new Vector4(.215f,.753f,.198f,.239f):
                brick?new Vector4(.423f,.668f,.202f,.160f):new Vector4(.005f,.253f,.203f,.243f));
            m.SetTextureScale("_BaseMap",wood?new Vector2(1,.45f):plaster?Vector2.one*.32f:Vector2.one*.65f);
            m.SetColor("_BaseColor",wood?new Color(.61f,.54f,.46f):plaster?new Color(1.1f,1.02f,.86f):
                brick?new Color(1.05f,.66f,.48f):name=="calcaire"?new Color(1.08f,1.08f,1.08f):new Color(.98f,1,.98f));
            m.SetFloat("_BumpScale",wood?.4f:plaster?.2f:.65f);m.SetFloat("_Smoothness",.16f);
            m.SetFloat("_Weathering",.04f);m.SetFloat("_SnowBase",.6f);m.SetFloat("_SnowFactor",.16f);
            m.SetFloat("_Wind",0);m.SetFloat("_HasGlossMap",0);m.SetFloat("_HasMaskMap",0);
            m.SetColor("_EmissionColor",Color.black);m.enableInstancing=true;EditorUtility.SetDirty(m);
            return m;
        }
        public static void Apply()
        {
            var cache=new Dictionary<Material,Material>();int count=0;
            foreach(var root in new[]{GameObject.Find("Architecture"),GameObject.Find("Vie du village"),GameObject.Find("Décor tiers (Asset Store)")}.Where(o=>o))
            foreach(var r in root.GetComponentsInChildren<MeshRenderer>(true))
            {
                var slots=r.sharedMaterials;
                for(int i=0;i<slots.Length;i++)
                {
                    if(!cache.TryGetValue(slots[i],out var adapted))cache[slots[i]]=adapted=Adapt(slots[i],true);
                    if(adapted==slots[i])continue;
                    slots[i]=adapted;r.SetPropertyBlock(null,i);count++;
                }
                r.sharedMaterials=slots;
            }
            Debug.Log("CITADELLE_ARCHITECTURE_BLACKSMITH surfaces="+count);
        }
    }
}
