using System;
using System.Collections.Generic;
using System.Linq;
using System.Text.RegularExpressions;
using UnityEditor;
using UnityEngine;

namespace ForgeLocal3D
{
    // Décor tiers de l'Asset Store posé sur la scène déjà construite : forge et écurie du
    // hameau, clôtures, réserves, charrettes, puits, arbres morts, rochers et éboulis.
    // Les packs vivent sous Assets/Vendor, hors du dépôt public. Un pack absent se déclare
    // par -1 dans la vérification ; un pack présent qui ne pose rien fait échouer la construction.
    public static class CitadelDecor
    {
        const string Vendor="Assets/Vendor/";
        const string RocksPack=Vendor+"Rocks and Boulders 2/Rocks/";
        const string PolyPack=Vendor+"Polylised - Medieval Desert City/Prefabs/";
        const string ForgePack=Vendor+"3DForge/FantasyExteriors/Village & Towns/";
        public static int Rocks=-1,DeadTrees=-1,Props=-1,Buildings=-1,CliffRocks=-1;

        // La rotation et l'échelle de la racine du prefab redressent certains FBX : on les garde.
        sealed class Kind { public GameObject prefab; public Vector3 center,extents,scale; public Quaternion rotation; public string family; }
        sealed class Rule
        {
            public bool natural,tilt;
            public float maxRange=.3f,slope=.8f,sink,margin=1.2f;
            public Func<Collider,bool> ground,ignored;
        }
        static System.Random rng;
        static Transform landscape;static MeshCollider terrain;static CitadelTraversal walk;
        static int placedProps;
        static readonly Dictionary<string,Kind> kinds=new();
        static readonly Dictionary<string,Material> converted=new();
        static readonly Dictionary<string,int> rejects=new();
        static bool Reject(string why){rejects[why]=rejects.GetValueOrDefault(why)+1;return false;}

        static float R(float a,float b)=>a+(float)rng.NextDouble()*(b-a);
        static T Pick<T>(IList<T> list)=>list[rng.Next(list.Count)];
        static Vector3 P(float[] p)=>new Vector3(-p[0],p[2],-p[1]);
        static Vector3 Around(float min,float max){float a=R(0,Mathf.PI*2);return new Vector3(Mathf.Cos(a),0,Mathf.Sin(a))*R(min,max);}
        static bool Landscape(Collider c)=>c.transform.IsChildOf(landscape);
        static bool Relief(Collider c)=>c.name.StartsWith("falaise_")||c.name.StartsWith("montagne_");
        static bool Buildable(Collider c)=>c==terrain||Landscape(c)&&c.name.StartsWith("Socle_terrasses");
        static Rule PropRule()=>new Rule{ground=Buildable,ignored=Landscape};

        public static void Place(VillageV2Builder.SceneSpec spec,CitadelTraversal traversal)
        {
            Rocks=DeadTrees=Props=Buildings=CliffRocks=-1;placedProps=0;kinds.Clear();converted.Clear();
            rng=new System.Random(spec.seed);walk=traversal;
            landscape=GameObject.Find("Relief, eau et ouvrages").transform;
            terrain=landscape.GetComponentsInChildren<MeshCollider>().FirstOrDefault(c=>c.name.StartsWith("Terrain_vallee"));
            if(!terrain)throw new InvalidOperationException("Terrain_vallee sans collision");
            var root=new GameObject("Décor tiers (Asset Store)").transform;
            Physics.SyncTransforms();
            bool props=false;
            // Les grands volumes d'abord : ils demandent le plus de place libre.
            if(Present(ForgePack))
            {
                props=true;Buildings=Require(Hamlet(Group(root,"Forge et écurie du hameau")),"bâtiment 3DForge");
                Fences(Group(root,"Clôtures"));
            }
            if(Present(PolyPack))
            {
                props=true;Accessories(Group(root,"Réserves, charrettes et puits"));
                DeadTrees=Require(Trees(Group(root,"Arbres morts")),"arbre mort");
            }
            if(props)Props=Require(placedProps,"accessoire");
            if(Present(RocksPack))Rocks=Require(Boulders(spec,Group(root,"Rochers et éboulis")),"rocher");
            if(root.childCount==0)UnityEngine.Object.DestroyImmediate(root.gameObject);
            Debug.Log("CITADELLE_DECOR_TIERS "+spec.id+" batiments="+Buildings+" accessoires="+Props+" arbres_morts="+DeadTrees+" rochers="+Rocks);
        }

        static bool Present(string pack)
        {
            if(AssetDatabase.IsValidFolder(pack.TrimEnd('/')))return true;
            Debug.LogWarning("Pack tiers absent, décor non posé : "+pack);return false;
        }
        static int Require(int count,string what)
        {
            if(count==0)throw new InvalidOperationException("Aucun "+what+" posé alors que le pack est présent");
            return count;
        }
        static Transform Group(Transform root,string name){var t=new GameObject(name).transform;t.SetParent(root);return t;}
        static CitadelTraversal.Route[] Lanes(params string[] prefixes)
        {
            var lanes=walk.routes.Where(r=>prefixes.Any(p=>r.id.StartsWith(p))).ToArray();
            if(lanes.Length==0)throw new InvalidOperationException("Rues absentes : "+string.Join(",",prefixes));
            return lanes;
        }

        static Kind Load(string path,string family,Vector3? shape=null)
        {
            if(kinds.TryGetValue(path,out var known))return known;
            var prefab=AssetDatabase.LoadAssetAtPath<GameObject>(path);
            if(!prefab)throw new InvalidOperationException("Prefab tiers absent : "+path);
            if(prefab.GetComponentInChildren<LODGroup>(true))throw new InvalidOperationException("Prefab tiers avec LOD, compté comme une instance du manifeste : "+path);
            var probe=(GameObject)PrefabUtility.InstantiatePrefab(prefab);
            var rotation=prefab.transform.localRotation;var scale=Vector3.Scale(prefab.transform.localScale,shape??Vector3.one);
            // Les modèles Polylised sont exportés axe Z vers le haut, sans conversion à l'import (vu sur capture).
            if(family=="polylised"||family=="arbre")rotation=Quaternion.Euler(-90,0,0)*rotation;
            probe.transform.SetPositionAndRotation(Vector3.zero,rotation);probe.transform.localScale=scale;
            Convert(probe,family);var b=Bounds(probe);UnityEngine.Object.DestroyImmediate(probe);
            return kinds[path]=new Kind{prefab=prefab,center=b.center,extents=b.extents,rotation=rotation,scale=scale,family=family};
        }
        static Bounds Bounds(GameObject go)
        {
            var renderers=go.GetComponentsInChildren<Renderer>().Where(r=>r.enabled).ToArray();
            if(renderers.Length==0)throw new InvalidOperationException("Objet tiers sans rendu : "+go.name);
            var b=renderers[0].bounds;foreach(var r in renderers.Skip(1))b.Encapsulate(r.bounds);return b;
        }

        // Emplacement libre : hors des réserves du parcours, sol accepté sous toute l'emprise,
        // dénivelé borné, et aucune collision autre que celles que la règle ignore.
        static bool Fit(Kind k,Vector3 at,float yaw,float scale,Rule rule,out Vector3 pivot,out Vector3 normal,out float range)
        {
            pivot=normal=Vector3.zero;range=float.MaxValue;
            var rot=Quaternion.Euler(0,yaw,0);Vector3 e=k.extents*scale;
            if(Reserved(at,Mathf.Min(e.x,e.z),rule))return Reject("réserve");
            int sx=Mathf.Clamp(Mathf.CeilToInt(e.x/1.2f),1,6),sz=Mathf.Clamp(Mathf.CeilToInt(e.z/1.2f),1,6);
            float low=float.MaxValue,high=float.MinValue;
            for(int i=-sx;i<=sx;i++)for(int j=-sz;j<=sz;j++)
            {
                Vector3 p=at+rot*new Vector3(e.x*.95f*i/sx,0,e.z*.95f*j/sz);
                if(!Physics.Raycast(new Vector3(p.x,900,p.z),Vector3.down,out var hit,1800)||!rule.ground(hit.collider))return Reject("sol");
                if(hit.normal.y<rule.slope)return Reject("pente");
                low=Mathf.Min(low,hit.point.y);high=Mathf.Max(high,hit.point.y);normal+=hit.normal;
                if(high-low>rule.maxRange)return Reject("dénivelé");
            }
            float bottom=low-.03f-rule.sink*2*e.y;
            Physics.SyncTransforms();
            if(Physics.OverlapBox(new Vector3(at.x,bottom+e.y,at.z),new Vector3(e.x*.9f,e.y*.92f,e.z*.9f),rot).Any(c=>!rule.ignored(c)))return Reject("collision");
            Vector3 offset=rot*(k.center*scale);
            pivot=new Vector3(at.x-offset.x,bottom-(k.center.y-k.extents.y)*scale,at.z-offset.z);
            normal.Normalize();range=high-low;return true;
        }
        static bool Reserved(Vector3 c,float radius,Rule rule)
        {
            float bx=-c.x,by=-c.z;
            // Mêmes réserves que les sapins de fabriquer.py : ville haute, pont et hameau.
            if(rule.natural&&((bx/66)*(bx/66)+(by/57)*(by/57)<1.15f||Mathf.Abs(bx)<10&&by<-40||-136<bx&&bx<-61&&-80<by&&by<2))return true;
            // Le contrôle de parcours pose un mur près de l'arrivée et abat un sapin de la lisière.
            if(Flat(c-walk.spawn)<14+radius||Flat(c-walk.forest)<30+radius)return true;
            if(walk.plots.Any(p=>Flat(c-p.position)<p.size.magnitude/2+3+radius))return true;
            return Gap(c)<radius+rule.margin;
        }
        static float Flat(Vector3 v)=>new Vector2(v.x,v.z).magnitude;
        static float Gap(Vector3 c)
        {
            float best=float.MaxValue;var p=new Vector2(c.x,c.z);
            foreach(var route in walk.routes)for(int i=1;i<route.points.Length;i++)
            {
                Vector2 a=new(route.points[i-1].x,route.points[i-1].z),ab=new Vector2(route.points[i].x,route.points[i].z)-a;
                float t=ab.sqrMagnitude<1e-6f?0:Mathf.Clamp01(Vector2.Dot(p-a,ab)/ab.sqrMagnitude);
                // L'accotement exporté par Blender déborde de 0,5 m de chaque côté.
                best=Mathf.Min(best,Vector2.Distance(p,a+ab*t)-route.width/2-.5f);
            }
            return best;
        }
        static GameObject Put(Kind k,Transform parent,string name,Vector3 at,float yaw,float scale,Rule rule)
        {
            if(!Fit(k,at,yaw,scale,rule,out var pivot,out var normal,out _))return null;
            var go=(GameObject)PrefabUtility.InstantiatePrefab(k.prefab,parent);go.name=name;
            var rot=Quaternion.Euler(0,yaw,0);
            if(rule.tilt)rot=Quaternion.FromToRotation(Vector3.up,Vector3.Slerp(Vector3.up,normal,.6f))*Quaternion.Euler(R(-7,7),0,R(-7,7))*rot;
            go.transform.SetPositionAndRotation(pivot,rot*k.rotation);go.transform.localScale=k.scale*scale;
            Convert(go,k.family);
            if(k.family=="polylised")
                foreach(var f in go.GetComponentsInChildren<MeshFilter>())f.gameObject.AddComponent<MeshCollider>().sharedMesh=f.sharedMesh;
            Physics.SyncTransforms();return go;
        }
        // Le long d'une rue, du côté tiré au sort ; le grand côté de l'objet suit la rue.
        static void Slot(CitadelTraversal.Route[] lanes,Kind k,float scale,float gap,out Vector3 at,out float yaw)
        {
            var route=Pick(lanes);int i=rng.Next(route.points.Length);
            Vector3 t=route.points[Mathf.Min(i+1,route.points.Length-1)]-route.points[Mathf.Max(i-1,0)];t.y=0;t.Normalize();
            at=route.points[i]+new Vector3(t.z,0,-t.x)*(rng.Next(2)*2-1)*(route.width/2+.5f+Mathf.Min(k.extents.x,k.extents.z)*scale+gap);
            yaw=Yaw(t,k)+rng.Next(2)*180;
        }
        static float Yaw(Vector3 t,Kind k)=>Mathf.Atan2(t.x,t.z)*Mathf.Rad2Deg-(k.extents.x>k.extents.z?90:0);

        static int Hamlet(Transform parent)
        {
            var lanes=Lanes("ruelle_hameau","liaison_hameau","rue_basse","traverse_village","descente_village","lisiere_bois","acces_terrain");
            var rule=new Rule{maxRange=2.8f,slope=.5f,margin=2,ground=Buildable,ignored=Landscape};
            int count=0;
            foreach(var (path,name) in new[]{("Buildings/ForestVillage/Smithy","forge"),("Buildings/Farm/Stables/Stable_2horse","ecurie")})
            {
                var k=Load(ForgePack+"Prefabs/"+path+".prefab","3dforge");
                // Plusieurs emplacements au bord des rues du bas : on garde l'assise la plus plate.
                float best=float.MaxValue,bestYaw=0;Vector3 bestAt=default;rejects.Clear();
                for(int i=0;i<2000;i++)
                {
                    Slot(lanes,k,1,R(2,14),out var at,out var yaw);
                    if(Fit(k,at,yaw,1,rule,out _,out _,out float range)&&range<best){best=range;bestAt=at;bestYaw=yaw;}
                }
                if(best==float.MaxValue)
                {Debug.LogWarning("Aucune assise libre pour "+path+" : "+string.Join(", ",rejects.Select(r=>r.Key+"="+r.Value)));continue;}
                var go=Put(k,parent,name,bestAt,bestYaw,1,rule);
                if(!go)throw new InvalidOperationException("Assise perdue : "+name);
                Foundation(go,k,best,bestYaw);count++;
                if(name=="ecurie")Troughs(go,bestYaw,parent);
            }
            return count;
        }
        public static void AddForgeView(CitadelEnvironment env)
        {
            var forge=GameObject.Find("forge");if(!forge)return;
            var b=Bounds(forge);var target=b.center;Vector3 chosen=default;float best=-1;
            Physics.SyncTransforms();
            for(int level=0;level<2;level++)for(int i=0;i<16;i++)
            {
                float angle=i*Mathf.PI/8;
                float distance=Mathf.Max(b.size.x,b.size.z)*1.3f;
                var position=target+new Vector3(Mathf.Sin(angle)*distance,4+level*5,Mathf.Cos(angle)*distance);
                if(Physics.Raycast(new Vector3(position.x,900,position.z),Vector3.down,out var ground,1800))position.y=Mathf.Max(position.y,ground.point.y+2);
                float score=0;
                foreach(var aim in new[]{target,target+Vector3.up*b.extents.y*.6f,target+Vector3.right*b.extents.x*.5f,target-Vector3.right*b.extents.x*.5f})
                {
                    var ray=aim-position;
                    bool blocked=Physics.RaycastAll(position,ray.normalized,ray.magnitude).Any(h=>!h.collider.transform.IsChildOf(forge.transform));
                    if(!blocked)score+=1;
                }
                score-=level*.08f;
                if(score>best){best=score;chosen=position;}
            }
            if(best<2)throw new InvalidOperationException("Forge sans cadrage dégagé");
            env.viewpoints=env.viewpoints.Where(v=>v.name!="Forge").Append(new CitadelEnvironment.Viewpoint{name="Forge",position=chosen,target=target,fieldOfView=52}).ToArray();
        }
        // Réexécutable sans reconstruire les paysages : cadrages, preuves et sauvegarde.
        public static void CaptureBuildings()
        {
            foreach(string path in System.IO.Directory.GetFiles(CitadelBuilder.Root+"/Scenes","Forge_Citadelle_*.unity"))
            {
                UnityEditor.SceneManagement.EditorSceneManager.OpenScene(path);
                var env=UnityEngine.Object.FindFirstObjectByType<CitadelEnvironment>();AddForgeView(env);
                string id=System.IO.Path.GetFileNameWithoutExtension(path).Replace("Forge_Citadelle_","");
                UnityEditor.SceneManagement.EditorSceneManager.SaveScene(UnityEngine.SceneManagement.SceneManager.GetActiveScene());
                var point=env.viewpoints.Single(v=>v.name=="Forge");
                env.view.transform.position=point.position;env.view.transform.LookAt(point.target);env.view.fieldOfView=point.fieldOfView;
                CitadelPlayCheck.Capture(env.view,System.IO.Path.GetFullPath("../local3d/citadelle/sorties/villages/"+id+"/renders/unity_forge.png"),1600,900);
            }
        }

        static void Foundation(GameObject building,Kind kind,float range,float yaw)
        {
            // La dalle remonte le bâtiment au-dessus du point haut sans déplacer les rues.
            building.transform.position+=Vector3.up*(range+.08f);
            var bounds=Bounds(building);
            var baseObject=GameObject.CreatePrimitive(PrimitiveType.Cube);baseObject.name="Soubassement pierre";
            baseObject.transform.position=new Vector3(bounds.center.x,bounds.min.y-range*.5f-.14f,bounds.center.z);
            baseObject.transform.localScale=new Vector3(kind.extents.x*1.88f,range+.28f,kind.extents.z*1.88f);
            baseObject.transform.rotation=Quaternion.Euler(0,yaw,0);
            baseObject.GetComponent<Renderer>().sharedMaterial=Scene("pierre_taille");
            baseObject.transform.SetParent(building.transform,true);
        }
        static void Troughs(GameObject stable,float yaw,Transform parent)
        {
            var b=Bounds(stable);
            foreach(var path in new[]{"fi_vil_farm_trough02_2m","fi_vil_farm_trough02_1m"})
            {
                var k=Load(ForgePack+"Prefabs/Buildings/Farm/Troughs/"+path+".prefab","3dforge");
                for(int i=0;i<80;i++)
                    if(Put(k,parent,"abreuvoir_"+placedProps,b.center+Around(Mathf.Max(b.extents.x,b.extents.z)+.8f,Mathf.Max(b.extents.x,b.extents.z)+3),yaw+rng.Next(4)*90,1,PropRule())){placedProps++;break;}
            }
        }
        static void Fences(Transform parent)
        {
            var set=new[]{"fi_vil_fence02_2,5m_B","fi_vil_fence02_2,5m_C"}.Select(n=>Load(ForgePack+"Prefabs/Fences/Fence02/"+n+".prefab","3dforge")).ToArray();
            var rule=PropRule();rule.maxRange=.45f;
            foreach(var route in Lanes("acces_terrain","lisiere_bois","descente_village"))
            {
                // Une clôture d'un seul côté, interrompue là où le sol, un arbre ou un seuil l'empêche.
                var d=new float[route.points.Length];
                for(int i=1;i<d.Length;i++)d[i]=d[i-1]+Flat(route.points[i]-route.points[i-1]);
                if(d[^1]<20)continue;
                float side=rng.Next(2)*2-1,step=Mathf.Max(set[0].extents.x,set[0].extents.z)*2*.97f;
                float s=R(.15f,.4f)*d[^1],end=Mathf.Min(d[^1]*.9f,s+R(18,40));
                for(;s<end;s+=step)
                {
                    int i=Mathf.Clamp(Array.FindIndex(d,x=>x>=s),1,d.Length-1);
                    Vector3 a=route.points[i-1],b=route.points[i],t=b-a;t.y=0;float f=Mathf.InverseLerp(d[i-1],d[i],s);t.Normalize();
                    var k=Pick(set);
                    var at=Vector3.Lerp(a,b,f)+new Vector3(t.z,0,-t.x)*side*(route.width/2+.5f+Mathf.Min(k.extents.x,k.extents.z)+1.3f);
                    if(Put(k,parent,"cloture_"+placedProps,at,Yaw(t,k),1,rule))placedProps++;
                }
            }
        }

        static void Accessories(Transform parent)
        {
            string Prop(string name)=>PolyPack+"prefab_props/"+name+".prefab";
            // Hauteurs cibles plausibles : le pack n'est pas à l'échelle de la citadelle.
            var stores=new[]{(Load(Prop("barrel"),"polylised"),1.05f),(Load(Prop("barrel_group"),"polylised"),1.1f),(Load(Prop("box"),"polylised"),.75f)};
            var houses=UnityEngine.Object.FindObjectsByType<LODGroup>(FindObjectsSortMode.None).Where(g=>g.name.StartsWith("maison_")).OrderBy(g=>g.name).OrderBy(_=>rng.Next()).Take(26).ToArray();
            foreach(var house in houses)
            {
                var hb=Bounds(house.gameObject);float r=Mathf.Max(hb.extents.x,hb.extents.z);
                for(int i=0;i<14;i++)
                {
                    var (k,height)=Pick(stores);
                    if(Put(k,parent,"reserve_"+placedProps,hb.center+Around(r*.55f+.3f,r+1.4f),R(0,360),height/(k.extents.y*2),PropRule())){placedProps++;break;}
                }
            }
            // La démo du pack aplatit toujours la charrette ainsi (1,11 ; 0,97 ; 0,49 dans le repère du FBX).
            var wagon=Load(Prop("wagon"),"polylised",new Vector3(1,.87f,.44f));float wagonScale=3.4f/(2*Mathf.Max(wagon.extents.x,wagon.extents.z));
            var roads=Lanes("descente_village","rue_basse","lisiere_bois","liaison_hameau");var sloped=PropRule();sloped.maxRange=.5f;
            for(int placed=0,i=0;placed<3&&i<300;i++)
            {
                Slot(roads,wagon,wagonScale,R(.8f,3),out var at,out var yaw);
                if(Put(wagon,parent,"charrette_"+placed,at,yaw,wagonScale,sloped)){placed++;placedProps++;}
            }
            var well=Load(Prop("well"),"polylised");float wellScale=2.4f/(2*Mathf.Max(well.extents.x,well.extents.z));
            var hamlet=Lanes("ruelle_hameau","liaison_hameau","traverse_village");
            for(int i=0;i<400;i++)
            {
                Slot(hamlet,well,wellScale,R(1.5f,5),out var at,out var yaw);
                if(Put(well,parent,"puits",at,yaw,wellScale,PropRule())){placedProps++;break;}
            }
        }
        static int Trees(Transform parent)
        {
            var set=Enumerable.Range(0,10).Select(i=>Load(PolyPack+"prefab_trees/dead_tree_"+(char)('a'+i)+".prefab","arbre")).ToArray();
            var rule=new Rule{natural=true,maxRange=1.2f,slope=.78f,margin=1.5f,ground=c=>c==terrain,ignored=Landscape};
            int n=0;
            for(int i=0;i<900&&n<36;i++)
            {
                var k=Pick(set);float scale=R(5,9)/(k.extents.y*2);
                // L'emprise testée est celle du tronc : les branches passent au-dessus des sapins voisins.
                var trunk=new Kind{prefab=k.prefab,family=k.family,rotation=k.rotation,scale=k.scale,center=new Vector3(0,k.center.y,0),extents=new Vector3(.7f/scale,k.extents.y,.7f/scale)};
                var go=Put(trunk,parent,"arbre_mort_"+n,new Vector3(R(-290,290),0,R(-260,175)),R(0,360),scale,rule);
                if(!go)continue;
                // Le repère du FBX peut être couché : le tronc a son propre repère vertical.
                var foot=new GameObject("tronc").transform;foot.SetParent(go.transform,false);
                foot.SetPositionAndRotation(new Vector3(go.transform.position.x,Bounds(go).min.y,go.transform.position.z),Quaternion.identity);
                float s=foot.lossyScale.x;var capsule=foot.gameObject.AddComponent<CapsuleCollider>();
                capsule.radius=.22f/s;capsule.height=3/s;capsule.center=new Vector3(0,1.5f/s,0);n++;
            }
            return n;
        }
        static int Boulders(VillageV2Builder.SceneSpec spec,Transform parent)
        {
            var set=new[]{"Rock1A","Rock1B","Rock1C","Rock1D","Rock1E","Rock2","Rock3","Rock4A","Rock4B","Rock5A","Rock5B","Rock6A","Rock6B","Rock6C"}
                .Select(name=>Load(RocksPack+"Prefabs_snow/"+name+".prefab","rocher")).ToArray();
            // Les rochers s'enfoncent d'un cinquième et peuvent toucher falaises et autres rochers.
            var rule=new Rule{natural=true,tilt=true,maxRange=float.MaxValue,slope=.5f,sink=.22f,margin=1.5f,
                ground=c=>c==terrain||Landscape(c)&&c.name.StartsWith("Éboulis"),ignored=c=>Landscape(c)||Relief(c)||c.transform.IsChildOf(parent)};
            int n=0;
            bool Rock(Vector3 at,float size)
            {
                var k=Pick(set);
                if(n>=420||!Put(k,parent,"rocher_"+n.ToString("000"),at,R(0,360),size/(2*Mathf.Max(k.extents.x,Mathf.Max(k.extents.y,k.extents.z))),rule))return false;
                n++;return true;
            }
            CliffRocks=CliffFaces(spec,set,parent);
            // Gros blocs au pied des falaises ; leurs fragments restent groupés autour.
            foreach(var cliff in spec.instances.Where(i=>i.asset.StartsWith("falaise_")))
                for(int i=0,placed=0;i<10&&placed<3;i++)if(Rock(P(cliff.position)+Around(14,28),R(2.2f,6.5f)))placed++;
            for(int i=0;i<160;i++)
            {
                var center=new Vector3(R(-290,290),0,R(-260,175));
                if(!Rock(center,R(2.5f,7.5f)))continue;
                for(int j=rng.Next(2,6);j>0;j--)Rock(center+Around(2.5f,7),R(.6f,2.2f));
            }
            return n+CliffRocks;
        }

        static int CliffFaces(VillageV2Builder.SceneSpec spec,Kind[] set,Transform parent)
        {
            int count=0;
            foreach(var instance in spec.instances.Where(i=>i.asset.StartsWith("falaise_")))
            {
                var cliff=GameObject.Find(instance.id);var bounds=Bounds(cliff);
                var outward=new Vector3(cliff.transform.position.x,0,cliff.transform.position.z).normalized;
                if(outward.sqrMagnitude<.5f)continue;
                var colliders=cliff.GetComponentsInChildren<MeshCollider>();
                foreach(float band in new[]{.22f,.65f})
                {
                    var center=bounds.center;center.y=Mathf.Lerp(bounds.min.y,bounds.max.y,band);
                    var ray=new Ray(center+outward*100,-outward);
                    var hits=new List<RaycastHit>();foreach(var c in colliders)if(c.Raycast(ray,out var hit,200))hits.Add(hit);
                    if(hits.Count==0)continue;var face=hits.OrderBy(h=>h.distance).First();
                    var kind=Pick(set);float size=R(11,17),scale=size/(2*Mathf.Max(kind.extents.x,Mathf.Max(kind.extents.y,kind.extents.z)));
                    var rotation=Quaternion.Euler(R(-12,12),R(0,360),R(-12,12))*kind.rotation;
                    var ext=kind.extents*scale;
                    // L'assise pénètre dans la paroi. Les volumes des accès restent libres à toute hauteur.
                    var position=face.point-outward*size*.37f;
                    if(Gap(position)<Mathf.Max(ext.x,ext.z)+2.5f)continue;
                    if(Physics.OverlapBox(position,ext*.9f,rotation).Any(c=>!Landscape(c)&&!Relief(c)&&!c.transform.IsChildOf(parent)))continue;
                    var go=(GameObject)PrefabUtility.InstantiatePrefab(kind.prefab,parent);
                    go.name="paroi_rocheuse_"+count.ToString("000");go.transform.localScale=kind.scale*scale;
                    go.transform.SetPositionAndRotation(position-rotation*(kind.center*scale),rotation);
                    Convert(go,"rocher");Physics.SyncTransforms();count++;
                }
            }
            if(count==0)throw new InvalidOperationException("Aucune paroi rocheuse posée avec le pack présent");
            Debug.Log("CITADELLE_PAROIS_ROCHEUSES "+spec.id+" blocs="+count);return count;
        }

        // Les shaders Standard des packs ne rendent pas sous URP : chaque matériau devient un
        // matériau de la citadelle, pour partager sa lumière, son brouillard et sa nuit.
        static void Convert(GameObject go,string family)
        {
            foreach(var r in go.GetComponentsInChildren<Renderer>(true))
            {
                var materials=r.sharedMaterials;
                if(materials.Any(m=>m&&m.name.EndsWith("colider"))){r.enabled=false;continue;}
                r.sharedMaterials=materials.Select(m=>Citadel(m,family)).ToArray();
            }
        }
        static Material Citadel(Material source,string family)
        {
            if(!source)throw new InvalidOperationException("Matériau tiers vide ("+family+")");
            string key=family+"/"+source.name;
            if(converted.TryGetValue(key,out var done))return done;
            Material result=null;string n=source.name;
            if(family=="rocher")
            {
                var digit=Regex.Match(n,@"^Rock(\d)").Groups[1].Value;
                if(digit!="")result=Lit("rocher_neige_"+digit,RocksPack+"Source/Textures/Rock"+digit+"_snow.tif",RocksPack+"Source/Textures/Rock"+digit+"_nmp.tif",.8f,.12f,Color.white);
            }
            else if(family=="arbre"&&n.StartsWith("Wood"))result=Scene("bois_noir");
            else if(family=="polylised")
            {
                if(n.StartsWith("Wood")||n.StartsWith("Rope"))result=Scene("bois_vieux");
                else if(n.StartsWith("Metal"))result=Scene("fer_noir");
                else if(n=="Wall_0")result=Scene("pierre_taille");
                else if(n=="Wall_1")result=Scene("calcaire");
                else if(n.StartsWith("Water"))result=Scene("neige_givre");
                else if(n.StartsWith("Cloth"))result=Lit("toile_ecrue",Texture("enduit_BaseColor"),Texture("enduit_Normal"),.3f,.08f,new Color(.86f,.8f,.64f));
            }
            else if(family=="3dforge")
            {
                if(n=="fe_village_base")result=Lit("village_3dforge",ForgePack+"Textures/fe_village_base.png",ForgePack+"Textures/fe_village_base_NRM.png",.7f,.14f,Color.white);
                else if(n=="fe_village_CORE")result=Lit("village_3dforge_coeur",ForgePack+"Textures/fe_village_base_CORE.png",null,.4f,.1f,Color.white);
            }
            if(!result)throw new InvalidOperationException("Matériau tiers sans correspondance : "+n+" ("+family+")");
            return converted[key]=result;
        }
        static string Texture(string name)=>CitadelBuilder.Root+"/Textures/"+name+".png";
        static Material Scene(string name)
        {
            var m=AssetDatabase.LoadAssetAtPath<Material>(CitadelBuilder.Root+"/Materials/"+name+".mat");
            if(!m)throw new InvalidOperationException("Matériau de la citadelle absent : "+name);
            return m;
        }
        static Material Lit(string name,string colorPath,string normalPath,float bump,float smoothness,Color tint)
        {
            string folder=CitadelBuilder.Root+"/Materials/Tiers";
            if(!AssetDatabase.IsValidFolder(folder))AssetDatabase.CreateFolder(CitadelBuilder.Root+"/Materials","Tiers");
            var color=AssetDatabase.LoadAssetAtPath<Texture2D>(colorPath);
            if(!color)throw new InvalidOperationException("Texture tierce absente : "+colorPath);
            Texture2D normal=null;
            if(normalPath!=null)
            {
                var importer=AssetImporter.GetAtPath(normalPath) as TextureImporter;
                if(!importer)throw new InvalidOperationException("Normales tierces absentes : "+normalPath);
                if(importer.textureType!=TextureImporterType.NormalMap){importer.textureType=TextureImporterType.NormalMap;importer.SaveAndReimport();}
                normal=AssetDatabase.LoadAssetAtPath<Texture2D>(normalPath);
            }
            string path=folder+"/"+name+".mat";
            var m=AssetDatabase.LoadAssetAtPath<Material>(path);
            if(!m){m=new Material(Shader.Find("Forge/CitadelLit"));AssetDatabase.CreateAsset(m,path);}
            m.SetTexture("_BaseMap",color);m.SetColor("_BaseColor",tint);m.SetTexture("_BumpMap",normal);
            m.SetFloat("_BumpScale",bump);m.SetFloat("_Smoothness",smoothness);m.SetFloat("_Metallic",0);m.SetFloat("_HasGlossMap",0);
            m.SetFloat("_Weathering",0);m.SetFloat("_SnowFactor",0);m.SetFloat("_Wind",0);m.SetFloat("_Banner",0);m.SetFloat("_AlphaClip",0);
            if(name.StartsWith("village_3dforge")){m.SetFloat("_SnowBase",1);m.SetFloat("_SnowFactor",.95f);}
            m.enableInstancing=true;EditorUtility.SetDirty(m);return m;
        }
    }
}
