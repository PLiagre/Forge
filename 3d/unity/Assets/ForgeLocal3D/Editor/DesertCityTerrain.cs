using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;

namespace ForgeLocal3D
{
    // Ville du désert, étape 1 : le relief de paysage.py devient un Unity Terrain, que la
    // ville creusera et peindra à l'exécution. Les hauteurs, les couches et les touffes
    // viennent de local3d/desert/terrain.py ; rien n'est recalculé ici.
    //
    // Le contrôle rouvre la scène enregistrée et mesure l'écart avec paysage.field sur
    // l'échantillon écrit par Python. Chaque contre-épreuve dérègle le terrain en mémoire,
    // exige l'échec, puis restaure.
    public static class DesertCityTerrain
    {
        const string Root=DesertBuilder.Root+"/Ville";
        const string Output="../local3d/desert/sorties/ville/";
        const string Pack="Assets/Vendor/TerrainDemoScene_HDRP/";
        // Précision d'un Unity Terrain : hauteurs sur 16 bits, 32 766 niveaux utiles.
        const float Levels=32766f;

        [Serializable] public class Point{public string nature;public double x,y,field,grille;}
        [Serializable] public class Stat{public double mediane=-1,p95=-1,max=-1;}
        [Serializable] public class Fichier{public string nom,sha256;}
        [Serializable] public class Guelta{public double x,y,z,largeur,profondeur;}
        [Serializable] public class XY{public double x,y;}
        [Serializable] public class Data
        {
            public string implantation,source;public int graine,resolution,couches_resolution,details_resolution;
            public double taille,pas,@base,hauteur,tolerance_marchable;
            public string[] couches,touffes;public double[] couverture;public int[] nombre_touffes;
            public Fichier[] fichiers;public Point[] echantillon;public Stat ecart_grille;
            public Guelta guelta;public XY[] oued;public XY centre;
            public double horizon_taille;public int horizon_resolution;
        }
        [Serializable] class Selection{public string[] implantations;}
        [Serializable] public class Report
        {
            public string status="echec",implantation,scene;public int graine;
            public int points=-1,points_marchables=-1,points_hors_tolerance=-1;
            public Stat ecart_rendu=new Stat(),ecart_physique=new Stat(),ecart_grille=new Stat();
            public double ecart_marchable_max=-1,tolerance_marchable=-1,quantification=-1;
            public double transport_hauteurs=-1,transport_couches=-1,transport_horizon=-1;
            public int raccord_echantillons=-1,raccord_trous=-1;
            public double[] couverture;
            public int[] touffes=new int[0];public int touffes_sur_rue=-1,prototypes=-1;
            public bool pack_terrain_sample;
            public bool contre_epreuve_echantillon_vide,contre_epreuve_decalage_vertical,contre_epreuve_axes_permutes,contre_epreuve_couches_permutees,contre_epreuve_touffe_sur_rue,contre_epreuve_horizon_decale;
            public string[] captures=new string[0];
            public string[] defauts=new string[0];
        }

        static Vector3 P(double x,double y,double z)=>new Vector3((float)-x,(float)z,(float)-y);
        static string Folder(string id)=>Output+id+"/";

        public static void Start()
        {
            var previous=(GraphicsSettings.defaultRenderPipeline,QualitySettings.renderPipeline);
            int code=1;
            try
            {
                var selection=JsonUtility.FromJson<Selection>(File.ReadAllText(Output+"selection.json"));
                if(selection?.implantations==null||selection.implantations.Length==0)
                    throw new InvalidOperationException("Aucune implantation à construire : lancer py local3d/atelier_desert.py terrain");
                var pipeline=AssetDatabase.LoadAssetAtPath<RenderPipelineAsset>(DesertBuilder.Root+"/Settings/Pipeline.asset");
                if(!pipeline)throw new InvalidOperationException("Pipeline du désert absent : lancer d'abord py local3d/atelier_desert.py unity");
                GraphicsSettings.defaultRenderPipeline=pipeline;QualitySettings.renderPipeline=pipeline;
                bool ok=true;
                foreach(var id in selection.implantations)
                {
                    Build(id);
                    var report=Check(id);
                    File.WriteAllText(Folder(id)+"unity-terrain.json",JsonUtility.ToJson(report,true));
                    Debug.Log("DESERT_TERRAIN "+id+" "+report.status+" "+string.Join(" | ",report.defauts));
                    ok&=report.status=="valide";
                }
                code=ok?0:1;
            }
            catch(Exception e){Debug.LogException(e);code=1;}
            finally{GraphicsSettings.defaultRenderPipeline=previous.Item1;QualitySettings.renderPipeline=previous.Item2;}
            CitadelEditorBridge.Finish(code);
        }

        [MenuItem("Forge/Désert/Ville : terrain et contrôle")]
        public static void Menu()=>Start();

        // ---------- Lecture des données de Python ----------

        public static Data Load(string id)
        {
            string folder=Folder(id);
            var d=JsonUtility.FromJson<Data>(File.ReadAllText(folder+"terrain.json"));
            if(d==null||d.implantation!=id)throw new InvalidOperationException("terrain.json illisible ou d'une autre implantation : "+id);
            // Un fichier binaire plus récent ou plus ancien que son rapport est refusé.
            using var sha=SHA256.Create();
            foreach(var f in d.fichiers)
            {
                string hash=BitConverter.ToString(sha.ComputeHash(File.ReadAllBytes(folder+f.nom))).Replace("-","").ToLowerInvariant();
                if(hash!=f.sha256)throw new InvalidOperationException("Empreinte divergente : "+folder+f.nom);
            }
            return d;
        }
        static float[] Floats(string path,int count)
        {
            var bytes=File.ReadAllBytes(path);
            if(bytes.Length!=count*4)throw new InvalidOperationException("Taille inattendue : "+path);
            var values=new float[count];Buffer.BlockCopy(bytes,0,values,0,bytes.Length);return values;
        }
        static byte[] Bytes(string path,int count)
        {
            var bytes=File.ReadAllBytes(path);
            if(bytes.Length!=count)throw new InvalidOperationException("Taille inattendue : "+path);
            return bytes;
        }
        static float[,] Heights(Data d)
        {
            int n=d.resolution;var meters=Floats(Folder(d.implantation)+"hauteurs.f32",n*n);var h=new float[n,n];
            for(int j=0;j<n;j++)for(int i=0;i<n;i++)
            {
                float v=(float)((meters[j*n+i]-d.@base)/d.hauteur);
                if(v<0||v>1)throw new InvalidOperationException("Hauteur hors de la boîte du terrain");
                h[j,i]=v;
            }
            return h;
        }
        static float[,,] Splat(Data d)
        {
            int n=d.couches_resolution,k=d.couches.Length;var b=Bytes(Folder(d.implantation)+"couches.u8",n*n*k);var a=new float[n,n,k];
            for(int j=0;j<n;j++)for(int i=0;i<n;i++)for(int c=0;c<k;c++)a[j,i,c]=b[(j*n+i)*k+c]/255f;
            return a;
        }
        static int[,] Detail(Data d,int layer)
        {
            int n=d.details_resolution;var b=Bytes(Folder(d.implantation)+"details_"+d.touffes[layer]+".u8",n*n);var a=new int[n,n];
            for(int j=0;j<n;j++)for(int i=0;i<n;i++)a[j,i]=b[j*n+i];
            return a;
        }

        // ---------- Construction ----------

        static bool PackPresent=>AssetDatabase.IsValidFolder(Pack.TrimEnd('/'));
        static T Need<T>(string path) where T:UnityEngine.Object
        {
            var asset=AssetDatabase.LoadAssetAtPath<T>(path);
            if(!asset)throw new InvalidOperationException("Asset absent : "+path+" ; reconstruire le ksar (py local3d/atelier_desert.py unity)");
            return asset;
        }
        static Texture2D Tex(string name)=>Need<Texture2D>(DesertBuilder.Root+"/Textures/"+name+".png");

        static TerrainLayer Layer(string name,Texture2D diffuse,Texture2D normal,Texture2D mask,float tile,Color tint,float smoothness)
        {
            string path=Root+"/Couches/"+name+".terrainlayer";
            var layer=AssetDatabase.LoadAssetAtPath<TerrainLayer>(path);
            if(!layer){layer=new TerrainLayer();AssetDatabase.CreateAsset(layer,path);}
            layer.diffuseTexture=diffuse;layer.normalMapTexture=normal;layer.maskMapTexture=mask;
            layer.tileSize=new Vector2(tile,tile);layer.tileOffset=Vector2.zero;layer.normalScale=1;
            layer.diffuseRemapMin=Vector4.zero;layer.diffuseRemapMax=new Vector4(tint.r,tint.g,tint.b,1);
            layer.maskMapRemapMin=Vector4.zero;layer.maskMapRemapMax=Vector4.one;
            layer.smoothness=smoothness;layer.metallic=0;
            EditorUtility.SetDirty(layer);return layer;
        }
        static TerrainLayer[] Layers(Data d,out bool pack)
        {
            pack=PackPresent;
            var layers=new List<TerrainLayer>();
            foreach(var name in d.couches)
            {
                if(name=="sable")layers.Add(Layer("Ville_sable",Tex("sable_dune_BaseColor"),Tex("sable_dune_Normal"),null,7,Color.white,.08f));
                else if(name=="reg")
                {
                    // Le reg : galets du Terrain Sample, réchauffés ; sans le pack, le gravier procédural du désert.
                    if(pack)
                    {
                        var source=Need<TerrainLayer>(Pack+"Terrain/Layers/Pebbles_B.terrainlayer");
                        layers.Add(Layer("Ville_reg",source.diffuseTexture,source.normalMapTexture,source.maskMapTexture,3.2f,new Color(1.14f,.96f,.76f),.1f));
                    }
                    else layers.Add(Layer("Ville_reg",Tex("reg_gravier_BaseColor"),Tex("reg_gravier_Normal"),null,4,Color.white,.1f));
                }
                else if(name=="gres")layers.Add(Layer("Ville_gres",Tex("gres_ocre_BaseColor"),Tex("gres_ocre_Normal"),null,15,Color.white,.12f));
                else if(name=="terre")
                {
                    // Terre humide de l'oasis : sol herbeux du Terrain Sample, réchauffé ; la texture
                    // procédurale de jardin dessine des sillons cultivés, en moiré à distance.
                    if(pack)
                    {
                        var source=Need<TerrainLayer>(Pack+"Terrain/Layers/Grass_Soil_A.terrainlayer");
                        layers.Add(Layer("Ville_terre",source.diffuseTexture,source.normalMapTexture,source.maskMapTexture,4,new Color(1.05f,.92f,.72f),.05f));
                    }
                    else layers.Add(Layer("Ville_terre",Tex("sable_ombre_BaseColor"),Tex("sable_ombre_Normal"),null,5,new Color(.8f,.72f,.6f),.05f));
                }
                else throw new InvalidOperationException("Couche inconnue : "+name);
            }
            return layers.ToArray();
        }
        static Material TerrainMaterial(TerrainLayer[] layers)
        {
            string path=Root+"/Terrain_ville.mat";
            var shader=Shader.Find("Universal Render Pipeline/Terrain/Lit");
            if(!shader)throw new InvalidOperationException("Shader de terrain URP absent");
            var m=AssetDatabase.LoadAssetAtPath<Material>(path);
            if(!m){m=new Material(shader);AssetDatabase.CreateAsset(m,path);}
            m.shader=shader;m.enableInstancing=true;
            // Réglages que l'inspecteur du shader pose d'ordinaire lui-même.
            m.SetFloat("_EnableHeightBlend",0);m.DisableKeyword("_TERRAIN_BLEND_HEIGHT");
            m.SetFloat("_EnableInstancedPerPixelNormal",1);m.EnableKeyword("_TERRAIN_INSTANCED_PERPIXEL_NORMAL");
            bool masks=layers.Any(l=>l.maskMapTexture);
            if(masks)m.EnableKeyword("_MASKMAP");else m.DisableKeyword("_MASKMAP");
            m.EnableKeyword("_NORMALMAP");
            for(int i=0;i<layers.Length;i++)m.SetFloat("_LayerHasMask"+i,layers[i].maskMapTexture?1:0);
            EditorUtility.SetDirty(m);return m;
        }

        static GameObject Tuft(string name)
        {
            var source=Need<GameObject>(Pack+"Prefabs/Details/"+name+".prefab");
            var filter=source.GetComponent<MeshFilter>();var renderer=source.GetComponent<MeshRenderer>();
            if(!filter||!filter.sharedMesh||!renderer)throw new InvalidOperationException("Touffe sans maillage à la racine : "+name);
            bool bush=name.StartsWith("Bush");
            string matPath=Root+"/Touffes/"+name+".mat";
            var shader=Shader.Find("Forge/CitadelLit");if(!shader)throw new InvalidOperationException("Shader Forge/CitadelLit absent");
            var m=AssetDatabase.LoadAssetAtPath<Material>(matPath);
            if(!m){m=new Material(shader);AssetDatabase.CreateAsset(m,matPath);}
            m.shader=shader;m.shaderKeywords=Array.Empty<string>();m.enableInstancing=true;
            var original=renderer.sharedMaterial;
            m.SetTexture("_BaseMap",CitadelTerrainSample.SavedTexture(original,"_BaseColorMap","Texture2D_E1B0D043"));
            m.SetTexture("_BumpMap",CitadelTerrainSample.SavedTexture(original,"_NormalMap","Texture2D_9DCAAA49"));
            m.SetTexture("_MaskMap",CitadelTerrainSample.SavedTexture(original,"_MaskMap","Texture2D_A5E0646"));
            m.SetFloat("_HasMaskMap",1);m.SetFloat("_HasGlossMap",0);m.SetFloat("_Metallic",0);m.SetFloat("_Smoothness",.2f);
            m.SetFloat("_BumpScale",.5f);m.SetFloat("_SnowFactor",0);m.SetFloat("_SnowBase",0);m.SetFloat("_Weathering",0);
            m.SetFloat("_Wind",bush?.08f:.2f);m.SetFloat("_WindHeight",1);m.SetFloat("_AlphaClip",1);m.SetFloat("_Cutoff",.38f);
            // Paille sèche pour les herbes, gris-vert poussiéreux pour les broussailles de l'oued.
            m.SetColor("_BaseColor",bush?new Color(.78f,.74f,.58f):new Color(.96f,.80f,.56f));m.SetColor("_EmissionColor",Color.black);
            m.renderQueue=(int)RenderQueue.AlphaTest;m.SetOverrideTag("RenderType","TransparentCutout");
            EditorUtility.SetDirty(m);
            var go=new GameObject(name);
            go.AddComponent<MeshFilter>().sharedMesh=filter.sharedMesh;
            var r=go.AddComponent<MeshRenderer>();r.sharedMaterial=m;r.shadowCastingMode=bush?ShadowCastingMode.On:ShadowCastingMode.Off;
            var prefab=PrefabUtility.SaveAsPrefabAsset(go,Root+"/Touffes/"+name+".prefab");
            UnityEngine.Object.DestroyImmediate(go);return prefab;
        }
        static DetailPrototype[] Prototypes(Data d)
        {
            return d.touffes.Select(name=>
            {
                bool bush=name.StartsWith("Bush");
                var p=new DetailPrototype
                {
                    prototype=Tuft(name),usePrototypeMesh=true,renderMode=DetailRenderMode.VertexLit,useInstancing=true,
                    minWidth=bush?.8f:.7f,maxWidth=bush?1.4f:1.2f,minHeight=bush?.7f:.6f,maxHeight=bush?1.3f:1.1f,
                    noiseSpread=.35f,healthyColor=Color.white,dryColor=new Color(.92f,.86f,.76f),
                    alignToGround=bush?.2f:.6f,positionJitter=.95f,density=1,useDensityScaling=true,
                };
                if(!p.Validate(out string message))throw new InvalidOperationException("Touffe refusée par Unity : "+name+" : "+message);
                return p;
            }).ToArray();
        }

        static Mesh Water(Data d)
        {
            var g=d.guelta;float rx=(float)(g.largeur*.5+8),ry=(float)(g.profondeur*.5+8);const int n=48;
            var v=new Vector3[n+1];v[0]=P(g.x,g.y,g.z);
            for(int k=0;k<n;k++){float a=k*Mathf.PI*2/n;v[k+1]=P(g.x+Mathf.Cos(a)*rx,g.y+Mathf.Sin(a)*ry,g.z);}
            var t=new List<int>();
            for(int k=0;k<n;k++)
            {
                int a=k+1,b=(k+1)%n+1;
                // Le miroir d'axes inverse le sens des triangles : l'eau doit regarder le ciel.
                if(Vector3.Cross(v[a]-v[0],v[b]-v[0]).y>0)t.AddRange(new[]{0,a,b});else t.AddRange(new[]{0,b,a});
            }
            var mesh=new Mesh{name="Eau de la guelta",vertices=v,triangles=t.ToArray()};
            mesh.uv=v.Select(p=>new Vector2(p.x/8,p.z/8)).ToArray();mesh.RecalculateNormals();mesh.RecalculateBounds();
            string path=Root+"/Eau_"+d.implantation+".asset";AssetDatabase.DeleteAsset(path);AssetDatabase.CreateAsset(mesh,path);
            return mesh;
        }

        // Horizon de dunes : paysage.field au pas de 16 m jusqu'à 1,5 km, sans le carré du terrain.
        // Un rideau vertical ferme la fente entre le bord du terrain (pas de 0,5 m) et celui de
        // l'horizon (pas de 16 m) : aucune vue rasante ne passe dessous.
        static GameObject Horizon(Terrain terrain,Data d)
        {
            int n=d.horizon_resolution;float H=(float)d.horizon_taille,s=H/(n-1),half=(float)(d.taille/2);
            var hm=Floats(Folder(d.implantation)+"horizon.f32",n*n);
            if(Mathf.Abs(half/s-Mathf.Round(half/s))>1e-4f)throw new InvalidOperationException("Le bord du terrain ne tombe pas sur la grille de l'horizon");
            var v=new Vector3[n*n];
            for(int j=0;j<n;j++)for(int i=0;i<n;i++)v[j*n+i]=new Vector3(i*s-H/2,hm[j*n+i],j*s-H/2);
            var tris=new List<int>();
            bool Inside(Vector3 p)=>Mathf.Abs(p.x)<=half+1e-3f&&Mathf.Abs(p.z)<=half+1e-3f;
            for(int j=0;j<n-1;j++)for(int i=0;i<n-1;i++)
            {
                int a=j*n+i,b=a+1,c=a+n,e=c+1;
                if(Inside(v[a])&&Inside(v[b])&&Inside(v[c])&&Inside(v[e]))continue;
                tris.AddRange(Vector3.Cross(v[c]-v[a],v[b]-v[a]).y>0?new[]{a,c,b,b,c,e}:new[]{a,b,c,b,e,c});
            }
            var mesh=new Mesh{name="Horizon "+d.implantation,indexFormat=IndexFormat.UInt32};
            mesh.vertices=v;mesh.triangles=tris.ToArray();
            mesh.uv=v.Select(p=>new Vector2(p.x,p.z)).ToArray();mesh.RecalculateNormals();mesh.RecalculateBounds();
            string path=Root+"/Horizon_"+d.implantation+".asset";AssetDatabase.DeleteAsset(path);AssetDatabase.CreateAsset(mesh,path);
            // Rideau : une colonne par échantillon du bord du terrain, du plus bas au plus haut des deux bords.
            var td=terrain.terrainData;int r=td.heightmapResolution;var o=terrain.transform.position;float step=(float)d.taille/(r-1);
            var hs=td.GetHeights(0,0,r,r);var cv=new List<Vector3>();var ct=new List<int>();
            float SkirtEdge(float x,float z)
            {
                // Le bord de l'horizon est linéaire entre deux sommets de sa grille.
                float u=(x+H/2)/s,w=(z+H/2)/s;int i=Mathf.Clamp(Mathf.FloorToInt(u),0,n-2),j=Mathf.Clamp(Mathf.FloorToInt(w),0,n-2);
                float fu=u-i,fw=w-j;
                return Mathf.Lerp(Mathf.Lerp(hm[j*n+i],hm[j*n+i+1],fu),Mathf.Lerp(hm[(j+1)*n+i],hm[(j+1)*n+i+1],fu),fw);
            }
            foreach(var side in new[]{0,1,2,3})
            {
                int start=cv.Count;
                for(int k=0;k<r;k++)
                {
                    int i=side==0?k:side==1?r-1:side==2?r-1-k:0,j=side==0?0:side==1?k:side==2?r-1:r-1-k;
                    float x=o.x+i*step,z=o.z+j*step,top=o.y+hs[j,i]*td.size.y,outer=SkirtEdge(x,z);
                    cv.Add(new Vector3(x,Mathf.Max(top,outer)+.02f,z));cv.Add(new Vector3(x,Mathf.Min(top,outer)-.3f,z));
                }
                for(int k=0;k<r-1;k++){int a=start+2*k;ct.AddRange(new[]{a,a+2,a+1,a+1,a+2,a+3,a,a+1,a+2,a+1,a+3,a+2});}
            }
            var curtain=new Mesh{name="Raccord "+d.implantation,indexFormat=IndexFormat.UInt32};
            curtain.vertices=cv.ToArray();curtain.triangles=ct.ToArray();
            curtain.uv=cv.Select(p=>new Vector2(p.x+p.z,p.y)).ToArray();curtain.RecalculateNormals();curtain.RecalculateBounds();
            string cpath=Root+"/Raccord_"+d.implantation+".asset";AssetDatabase.DeleteAsset(cpath);AssetDatabase.CreateAsset(curtain,cpath);
            var shader=Shader.Find("Forge/CitadelLit");
            var m=AssetDatabase.LoadAssetAtPath<Material>(Root+"/Horizon_sable.mat");
            if(!m){m=new Material(shader);AssetDatabase.CreateAsset(m,Root+"/Horizon_sable.mat");}
            m.shader=shader;m.shaderKeywords=Array.Empty<string>();
            m.SetTexture("_BaseMap",Tex("sable_dune_BaseColor"));m.SetTexture("_BumpMap",Tex("sable_dune_Normal"));m.SetTextureScale("_BaseMap",new Vector2(1/7f,1/7f));
            m.SetFloat("_HasMaskMap",0);m.SetFloat("_HasGlossMap",0);m.SetFloat("_Metallic",0);m.SetFloat("_Smoothness",.08f);m.SetFloat("_BumpScale",.4f);
            m.SetFloat("_SnowFactor",0);m.SetFloat("_SnowBase",0);m.SetFloat("_Weathering",0);m.SetFloat("_Wind",0);m.SetFloat("_AlphaClip",0);
            m.SetColor("_BaseColor",Color.white);m.SetColor("_EmissionColor",Color.black);EditorUtility.SetDirty(m);
            var root=new GameObject("Horizon de dunes");
            var skirt=new GameObject("Dunes lointaines");skirt.transform.SetParent(root.transform);
            skirt.AddComponent<MeshFilter>().sharedMesh=mesh;skirt.AddComponent<MeshRenderer>().sharedMaterial=m;
            var seam=new GameObject("Raccord au terrain");seam.transform.SetParent(root.transform);
            seam.AddComponent<MeshFilter>().sharedMesh=curtain;var sr=seam.AddComponent<MeshRenderer>();sr.sharedMaterial=m;sr.shadowCastingMode=ShadowCastingMode.Off;
            return root;
        }

        static string ScenePath(string id)=>DesertBuilder.Root+"/Scenes/Forge_Desert_Ville_"+id+".unity";

        public static void Build(string id)
        {
            var d=Load(id);
            foreach(var f in new[]{Root,Root+"/Couches",Root+"/Touffes"})
                if(!AssetDatabase.IsValidFolder(f)){Directory.CreateDirectory(f);AssetDatabase.Refresh();}
            var layers=Layers(d,out bool pack);
            var td=new TerrainData{name="Terrain "+id};
            td.heightmapResolution=d.resolution;
            td.size=new Vector3((float)d.taille,(float)d.hauteur,(float)d.taille);
            // L'asset existe avant les couches : leurs textures de contrôle en deviennent des
            // sous-assets. Posées avant, elles ne sont pas enregistrées et disparaissent au
            // changement de scène (défaut trouvé par le contrôle).
            string dataPath=Root+"/Terrain_"+id+".asset";
            AssetDatabase.DeleteAsset(dataPath);AssetDatabase.CreateAsset(td,dataPath);
            td.SetHeights(0,0,Heights(d));
            td.alphamapResolution=d.couches_resolution;td.baseMapResolution=1024;
            td.terrainLayers=layers;
            td.SetAlphamaps(0,0,Splat(d));
            td.SetDetailResolution(d.details_resolution,32);
            td.SetDetailScatterMode(DetailScatterMode.InstanceCountMode);
            if(pack)
            {
                td.detailPrototypes=Prototypes(d);
                for(int k=0;k<d.touffes.Length;k++)td.SetDetailLayer(0,0,k,Detail(d,k));
            }
            else Debug.LogWarning("Terrain Sample absent : terrain sans touffes, compteurs à -1.");
            EditorUtility.SetDirty(td);AssetDatabase.SaveAssets();

            var scene=EditorSceneManager.NewScene(NewSceneSetup.EmptyScene,NewSceneMode.Single);
            var go=Terrain.CreateTerrainGameObject(td);go.name="Terrain du ksar";
            go.transform.position=new Vector3((float)(-d.taille/2),(float)d.@base,(float)(-d.taille/2));
            var terrain=go.GetComponent<Terrain>();
            terrain.materialTemplate=TerrainMaterial(layers);terrain.drawInstanced=true;
            terrain.heightmapPixelError=1;terrain.basemapDistance=320;
            terrain.detailObjectDistance=180;terrain.detailObjectDensity=1;
            terrain.shadowCastingMode=ShadowCastingMode.TwoSided;terrain.allowAutoConnect=false;

            Horizon(terrain,d);
            var water=new GameObject("Eau de la guelta");
            water.AddComponent<MeshFilter>().sharedMesh=Water(d);
            water.AddComponent<MeshRenderer>().sharedMaterial=Need<Material>(DesertBuilder.Root+"/Materials/eau_oasis.mat");

            var sun=new GameObject("Soleil").AddComponent<Light>();sun.type=LightType.Directional;sun.shadows=LightShadows.Soft;
            sun.shadowBias=.045f;sun.shadowNormalBias=.22f;RenderSettings.sun=sun;
            var camera=new GameObject("Caméra de la ville").AddComponent<Camera>();camera.tag="MainCamera";
            camera.nearClipPlane=.3f;camera.farClipPlane=2500;camera.fieldOfView=38;
            camera.gameObject.AddComponent<UniversalAdditionalCameraData>().renderPostProcessing=true;
            var centre=Ground(terrain,d.centre.x,d.centre.y);
            camera.transform.position=centre+new Vector3(210,170,230);camera.transform.LookAt(centre);
            var volume=new GameObject("Ambiance du désert").AddComponent<Volume>();volume.isGlobal=true;
            volume.sharedProfile=Need<VolumeProfile>(DesertBuilder.Root+"/Settings/Ambiance.asset");
            var env=new GameObject("Soleil et vent").AddComponent<DesertEnvironment>();
            env.village="Ville du désert — "+id;env.seed=d.graine;env.scenes=new string[0];env.labels=new string[0];
            env.viewpoints=new DesertEnvironment.Viewpoint[0];env.fires=new Light[0];env.smoke=new ParticleSystem[0];env.flames=new ParticleSystem[0];
            env.view=camera;env.sun=sun;env.sky=Need<Material>(DesertBuilder.Root+"/Settings/Ciel.mat");env.showPanel=false;env.hour=16.5f;env.Apply();
            // Lot 263 : les routes du joueur, posées à l'exécution sur une copie de ce terrain.
            var routes=new GameObject("Routes du joueur");
            var roads=routes.AddComponent<DesertRoads>();roads.terrain=terrain;roads.implantation=id;roads.graine=d.graine;
            // Textures qui se répètent sans bord : chemin_sable et chemin_dalle sont des bandes de route
            // (chaussée au centre, sable sur les côtés) ; répétées sur le terrain, elles le rayaient.
            roads.terreBattue=Layer("Ville_terre_battue",Tex("sable_ombre_BaseColor"),Tex("sable_ombre_Normal"),null,4,new Color(.78f,.64f,.5f),.04f);
            roads.paves=Layer("Ville_paves",Tex("souk_dalles_BaseColor"),Tex("souk_dalles_Normal"),null,4,Color.white,.12f);
            var tool=routes.AddComponent<DesertRoadTool>();tool.roads=roads;tool.view=camera;
            EditorSceneManager.SaveScene(scene,ScenePath(id));
            AssetDatabase.SaveAssets();
        }

        static Vector3 Ground(Terrain t,double x,double y)
        {
            var p=P(x,y,0);p.y=t.SampleHeight(p)+t.transform.position.y;return p;
        }

        // ---------- Contrôle ----------

        static double Percentile(List<double> values,double q)
        {
            if(values.Count==0)return -1;
            var s=values.OrderBy(v=>v).ToList();double k=(s.Count-1)*q;int a=(int)Math.Floor(k),b=Math.Min(a+1,s.Count-1);
            return s[a]+(s[b]-s[a])*(k-a);
        }
        static Stat Stats(List<double> values)=>new Stat{mediane=Percentile(values,.5),p95=Percentile(values,.95),max=values.Count==0?-1:values.Max()};
        static bool Walkable(Point p)=>p.nature=="rue"||p.nature=="seuil";

        // Mesure de l'échantillon ; renvoie les défauts trouvés. Un échantillon vide est un défaut.
        static List<string> Measure(Terrain terrain,Data d,Point[] sample,Report report)
        {
            var faults=new List<string>();
            if(sample==null||sample.Length==0){faults.Add("échantillon vide");return faults;}
            var td=terrain.terrainData;var origin=terrain.transform.position;
            Physics.SyncTransforms();
            float q=td.size.y/Levels;
            var render=new List<double>();var physics=new List<double>();int beyond=0,walkable=0,tufts=0;double walkMax=0;
            int n=td.detailResolution;var detail=Enumerable.Range(0,td.detailPrototypes.Length).Select(k=>td.GetDetailLayer(0,0,n,n,k)).ToArray();
            foreach(var p in sample)
            {
                var w=P(p.x,p.y,0);
                float nx=(w.x-origin.x)/td.size.x,nz=(w.z-origin.z)/td.size.z;
                double r=origin.y+td.GetInterpolatedHeight(nx,nz);
                double e=Math.Abs(r-p.field);render.Add(e);
                // La surface Unity doit valoir celle de la grille idéale, à la quantification près.
                if(e>Math.Abs(p.grille-p.field)+q+1e-4)beyond++;
                double f=double.NaN;
                if(Physics.Raycast(new Vector3(w.x,origin.y+td.size.y+50,w.z),Vector3.down,out var hit,td.size.y+200)&&hit.collider is TerrainCollider)
                    f=hit.point.y;
                double ep=double.IsNaN(f)?double.PositiveInfinity:Math.Abs(f-p.field);physics.Add(ep);
                if(Walkable(p))
                {
                    walkable++;walkMax=Math.Max(walkMax,Math.Max(e,ep));
                    int ci=Mathf.Clamp(Mathf.FloorToInt(nx*n),0,n-1),cj=Mathf.Clamp(Mathf.FloorToInt(nz*n),0,n-1);
                    foreach(var layer in detail)tufts+=layer[cj,ci];
                }
            }
            report.points=sample.Length;report.points_marchables=walkable;report.points_hors_tolerance=beyond;
            report.ecart_rendu=Stats(render);report.ecart_physique=Stats(physics);report.ecart_marchable_max=walkMax;
            report.tolerance_marchable=d.tolerance_marchable;report.quantification=q;report.touffes_sur_rue=tufts;
            if(beyond>0)faults.Add(beyond+" points s'écartent de paysage.field plus que la grille elle-même");
            if(walkable==0)faults.Add("aucun point de rue ni de seuil dans l'échantillon");
            if(walkMax>d.tolerance_marchable)faults.Add("sol marchable à "+walkMax.ToString("0.000")+" m de paysage.field");
            if(physics.Any(double.IsInfinity))faults.Add("collision du terrain absente sous "+physics.Count(double.IsInfinity)+" points");
            if(tufts>0)faults.Add(tufts+" touffes sur une rue ou un seuil");
            return faults;
        }
        static List<string> Transport(Terrain terrain,Data d,Report report)
        {
            var faults=new List<string>();var td=terrain.terrainData;int n=d.resolution;
            if(td.heightmapResolution!=n)faults.Add("résolution "+td.heightmapResolution+" au lieu de "+n);
            var meters=Floats(Folder(d.implantation)+"hauteurs.f32",n*n);var got=td.GetHeights(0,0,n,n);
            double worst=0;
            for(int j=0;j<n;j++)for(int i=0;i<n;i++)worst=Math.Max(worst,Math.Abs(got[j,i]*d.hauteur-(meters[j*n+i]-d.@base)));
            report.transport_hauteurs=worst;
            if(worst>d.hauteur/Levels)faults.Add("hauteurs importées à "+worst.ToString("0.0000")+" m du fichier");
            int m=d.couches_resolution,k=d.couches.Length;var bytes=Bytes(Folder(d.implantation)+"couches.u8",m*m*k);
            var a=td.GetAlphamaps(0,0,m,m);double splat=0;var cover=new double[k];
            for(int j=0;j<m;j++)for(int i=0;i<m;i++)for(int c=0;c<k;c++)
            {splat=Math.Max(splat,Math.Abs(a[j,i,c]*255-bytes[(j*m+i)*k+c]));cover[c]+=a[j,i,c];}
            report.transport_couches=splat;report.couverture=cover.Select(c=>c/(m*m)).ToArray();
            if(splat>.5)faults.Add("couches importées à "+splat.ToString("0.00")+"/255 du fichier");
            for(int c=0;c<k;c++)if(report.couverture[c]<=0)faults.Add("couche "+d.couches[c]+" absente");
            if(td.terrainLayers.Length!=k||td.terrainLayers.Any(l=>!l||!l.diffuseTexture))faults.Add("couche de terrain sans texture");
            if(PackPresent)
            {
                int dn=td.detailResolution;
                report.prototypes=td.detailPrototypes.Length;
                report.touffes=Enumerable.Range(0,td.detailPrototypes.Length).Select(l=>{var g=td.GetDetailLayer(0,0,dn,dn,l);int s=0;foreach(var v in g)s+=v;return s;}).ToArray();
                if(report.prototypes!=d.touffes.Length)faults.Add("prototypes de touffes manquants");
                else for(int l=0;l<d.touffes.Length;l++)
                {
                    if(d.nombre_touffes[l]<=0)faults.Add("aucune touffe "+d.touffes[l]+" à poser");
                    if(report.touffes[l]!=d.nombre_touffes[l])faults.Add("touffes "+d.touffes[l]+" : "+report.touffes[l]+" au lieu de "+d.nombre_touffes[l]);
                }
                foreach(var p in td.detailPrototypes)if(!p.Validate(out string message))faults.Add("touffe invalide : "+message);
            }
            return faults;
        }
        // Raccord : à chaque échantillon du bord, le rideau couvre le bord du terrain et celui de l'horizon.
        static List<string> Seam(Terrain terrain,Data d,Report report)
        {
            var faults=new List<string>();
            var root=GameObject.Find("Horizon de dunes");
            if(!root){faults.Add("horizon absent");return faults;}
            var skirt=root.transform.Find("Dunes lointaines").GetComponent<MeshFilter>();var seam=root.transform.Find("Raccord au terrain").GetComponent<MeshFilter>();
            int n=d.horizon_resolution;var hm=Floats(Folder(d.implantation)+"horizon.f32",n*n);
            var world=skirt.sharedMesh.vertices.Select(skirt.transform.TransformPoint).ToArray();double worst=0;
            if(world.Length!=n*n){faults.Add("horizon incomplet");return faults;}
            for(int k=0;k<n*n;k++)worst=Math.Max(worst,Math.Abs(world[k].y-hm[k]));
            report.transport_horizon=worst;
            if(worst>1e-3)faults.Add("horizon à "+worst.ToString("0.000")+" m de paysage.field");
            var td=terrain.terrainData;var o=terrain.transform.position;
            var cv=seam.sharedMesh.vertices.Select(seam.transform.TransformPoint).ToArray();
            float H=(float)d.horizon_taille,s=H/(n-1);int holes=0;
            for(int c=0;c+1<cv.Length;c+=2)
            {
                float x=cv[c].x,z=cv[c].z;
                float edge=o.y+td.GetInterpolatedHeight((x-o.x)/td.size.x,(z-o.z)/td.size.z);
                float u=(x-world[0].x)/s,w=(z-world[0].z)/s;int i=Mathf.Clamp(Mathf.FloorToInt(u),0,n-2),j=Mathf.Clamp(Mathf.FloorToInt(w),0,n-2);
                float fu=u-i,fw=w-j;
                float outer=Mathf.Lerp(Mathf.Lerp(world[j*n+i].y,world[j*n+i+1].y,fu),Mathf.Lerp(world[(j+1)*n+i].y,world[(j+1)*n+i+1].y,fu),fw);
                float lo=Mathf.Min(cv[c].y,cv[c+1].y)-1e-3f,hi=Mathf.Max(cv[c].y,cv[c+1].y)+1e-3f;
                if(edge<lo||edge>hi||outer<lo||outer>hi)holes++;
            }
            report.raccord_echantillons=cv.Length/2;report.raccord_trous=holes;
            if(cv.Length==0)faults.Add("rideau de raccord vide");
            if(holes>0)faults.Add(holes+" échantillons du bord sans raccord entre terrain et horizon");
            return faults;
        }
        static List<string> All(Terrain terrain,Data d,Point[] sample,Report report)
        {
            var faults=Transport(terrain,d,report);faults.AddRange(Seam(terrain,d,report));faults.AddRange(Measure(terrain,d,sample,report));return faults;
        }


        public static Report Check(string id)
        {
            var report=new Report{implantation=id,scene=ScenePath(id),pack_terrain_sample=PackPresent};
            var d=Load(id);report.graine=d.graine;report.ecart_grille=d.ecart_grille;
            EditorSceneManager.OpenScene(ScenePath(id),OpenSceneMode.Single);
            var terrain=UnityEngine.Object.FindObjectsByType<Terrain>(FindObjectsSortMode.None).SingleOrDefault();
            if(!terrain)throw new InvalidOperationException("Scène sans terrain unique : "+ScenePath(id));
            var faults=All(terrain,d,d.echantillon,report);
            var td=terrain.terrainData;
            var scratch=new Report();

            // Contre-épreuves : chacune doit faire échouer le contrôle, puis tout est restauré.
            report.contre_epreuve_echantillon_vide=Measure(terrain,d,new Point[0],scratch).Count>0;

            var origin=terrain.transform.position;terrain.transform.position=origin+Vector3.up*.5f;
            report.contre_epreuve_decalage_vertical=Measure(terrain,d,d.echantillon,scratch).Count>0;
            terrain.transform.position=origin;

            int n=td.heightmapResolution;var heights=td.GetHeights(0,0,n,n);var swapped=new float[n,n];
            for(int j=0;j<n;j++)for(int i=0;i<n;i++)swapped[j,i]=heights[i,j];
            td.SetHeights(0,0,swapped);
            report.contre_epreuve_axes_permutes=Measure(terrain,d,d.echantillon,scratch).Count>0;
            td.SetHeights(0,0,heights);

            int m=td.alphamapResolution;var splat=td.GetAlphamaps(0,0,m,m);var crossed=(float[,,])splat.Clone();
            for(int j=0;j<m;j++)for(int i=0;i<m;i++){crossed[j,i,0]=splat[j,i,1];crossed[j,i,1]=splat[j,i,0];}
            td.SetAlphamaps(0,0,crossed);
            report.contre_epreuve_couches_permutees=Transport(terrain,d,scratch).Count>0;
            td.SetAlphamaps(0,0,splat);

            if(td.detailPrototypes.Length>0)
            {
                var street=d.echantillon.First(p=>p.nature=="rue");var w=P(street.x,street.y,0);int dn=td.detailResolution;
                int ci=Mathf.FloorToInt((w.x-origin.x)/td.size.x*dn),cj=Mathf.FloorToInt((w.z-origin.z)/td.size.z*dn);
                var layer=td.GetDetailLayer(ci,cj,1,1,0);int before=layer[0,0];layer[0,0]=before+1;td.SetDetailLayer(ci,cj,0,layer);
                report.contre_epreuve_touffe_sur_rue=Measure(terrain,d,d.echantillon,scratch).Count>0;
                layer[0,0]=before;td.SetDetailLayer(ci,cj,0,layer);
            }
            else report.contre_epreuve_touffe_sur_rue=false;

            var horizon=GameObject.Find("Horizon de dunes").transform;var place=horizon.position;horizon.position=place+Vector3.up*2;
            report.contre_epreuve_horizon_decale=Seam(terrain,d,scratch).Count>0;
            horizon.position=place;

            // Après restauration, le contrôle repasse exactement.
            var after=All(terrain,d,d.echantillon,new Report());
            if(after.Count!=faults.Count)faults.Add("restauration incomplète après les contre-épreuves : "+string.Join(" ; ",after));
            foreach(var (ok,name) in new[]{(report.contre_epreuve_echantillon_vide,"échantillon vide"),(report.contre_epreuve_decalage_vertical,"décalage vertical"),
                (report.contre_epreuve_axes_permutes,"axes permutés"),(report.contre_epreuve_couches_permutees,"couches permutées"),(report.contre_epreuve_horizon_decale,"horizon décalé")})
                if(!ok)faults.Add("contre-épreuve sans effet : "+name);
            if(PackPresent&&!report.contre_epreuve_touffe_sur_rue)faults.Add("contre-épreuve sans effet : touffe sur une rue");

            report.captures=Captures(terrain,d,faults);
            report.defauts=faults.ToArray();report.status=faults.Count==0?"valide":"echec";
            return report;
        }

        // ---------- Captures ----------

        static string[] Captures(Terrain terrain,Data d,List<string> faults)
        {
            string folder=Folder(d.implantation)+"captures/";Directory.CreateDirectory(folder);
            var camera=UnityEngine.Object.FindFirstObjectByType<Camera>();var env=UnityEngine.Object.FindFirstObjectByType<DesertEnvironment>();
            var names=new List<string>();
            var centre=Ground(terrain,d.centre.x,d.centre.y);
            void Shot(string name,Vector3 from,Vector3 to,float fov,float hour)
            {
                env.hour=hour;env.Apply();
                camera.transform.position=from;camera.transform.LookAt(to);camera.fieldOfView=fov;
                var pixels=CitadelPlayCheck.Capture(camera,folder+name+".png",1600,900);
                // Une image uniforme est un rendu raté, pas une vue.
                float mean=0,dev=0;foreach(var p in pixels)mean+=p.r+p.g+p.b;mean/=pixels.Length;
                foreach(var p in pixels)dev+=Mathf.Abs(p.r+p.g+p.b-mean);dev/=pixels.Length;
                if(dev<6)faults.Add("capture uniforme : "+name);
                names.Add(name+".png");
            }
            Shot("ensemble",centre+new Vector3(260,190,290),centre,38,16.5f);
            Shot("ensemble_soir",centre+new Vector3(-280,150,240),centre,38,18.8f);
            // Au ras du reg : la cellule la plus garnie de touffes à moins de 200 m du centre.
            var td=terrain.terrainData;int dn=td.detailResolution;var origin=terrain.transform.position;
            if(td.detailPrototypes.Length>0)
            {
                var sum=new int[dn,dn];
                for(int l=0;l<td.detailPrototypes.Length;l++){var g=td.GetDetailLayer(0,0,dn,dn,l);for(int j=0;j<dn;j++)for(int i=0;i<dn;i++)sum[j,i]+=g[j,i];}
                int best=-1;Vector3 spot=centre;int cell=16;
                for(int j=0;j+cell<dn;j+=cell/2)for(int i=0;i+cell<dn;i+=cell/2)
                {
                    var c=new Vector3(origin.x+(i+cell/2f)*td.size.x/dn,0,origin.z+(j+cell/2f)*td.size.z/dn);
                    if(Vector2.Distance(new Vector2(c.x,c.z),new Vector2(centre.x,centre.z))>200)continue;
                    int s=0;for(int b=j;b<j+cell;b++)for(int a=i;a<i+cell;a++)s+=sum[b,a];
                    if(s>best){best=s;spot=c;}
                }
                spot.y=terrain.SampleHeight(spot)+origin.y;
                var eye=spot+new Vector3(11,0,-11);eye.y=terrain.SampleHeight(eye)+origin.y+1.8f;
                Shot("reg_et_touffes",eye,spot+Vector3.up*.3f,50,16.5f);
            }
            // Le lit de l'oued, vu dans son axe depuis son milieu.
            int k=d.oued.Length/2;var o=Ground(terrain,d.oued[k].x,d.oued[k].y);var o2=Ground(terrain,d.oued[Math.Min(k+6,d.oued.Length-1)].x,d.oued[Math.Min(k+6,d.oued.Length-1)].y);
            var along=(o2-o);along.y=0;along.Normalize();
            Shot("oued",o-along*25+Vector3.up*9,o2,45,16.5f);
            var g2=Ground(terrain,d.guelta.x,d.guelta.y);
            Shot("guelta",g2+new Vector3(45,22,-40),g2,42,17.5f);
            // Le cordon de dunes, depuis le bord de la plaine vers l'extérieur.
            var dir=new Vector3(-(float)d.centre.x,0,-(float)d.centre.y);dir=dir.sqrMagnitude<1?Vector3.forward:dir.normalized;
            var edge=centre+dir*140;edge.y=terrain.SampleHeight(edge)+origin.y+14;
            var far=centre+dir*330;far.y=terrain.SampleHeight(far)+origin.y;
            Shot("dunes",edge,far,45,17.5f);
            // Les anciens seuils et la rampe, gravés dans paysage.field.
            var pads=d.echantillon.Where(p=>p.nature=="seuil").ToArray();
            if(pads.Length>0)
            {
                var b=Ground(terrain,pads.Average(p=>p.x),pads.Average(p=>p.y));
                Shot("bourg",b+new Vector3(70,55,60),b,40,16.5f);
            }
            return names.ToArray();
        }
    }
}
