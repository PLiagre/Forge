using System;
using System.Collections.Generic;
using System.Linq;
using UnityEditor;
using UnityEngine;

namespace ForgeLocal3D
{
    // Décor tiers du pack « Polylised - Medieval Desert City » : tentes, chariots, tonneaux,
    // fontaine, puits, lampes et arbres morts. Blender ne le connaît pas : il n'entre ni dans
    // le manifeste ni dans la parité d'import. Pack absent : -1 ; pack présent sans pose : échec.
    public static class DesertDecor
    {
        const string Pack="Assets/Vendor/Polylised - Medieval Desert City/Prefabs/";
        public static int Props=-1,DeadTrees=-1;
        static System.Random rng;
        static Transform landscape;
        static CitadelTraversal walk;
        static readonly Dictionary<string,Material> converted=new();

        static float R(float a,float b)=>a+(float)rng.NextDouble()*(b-a);
        static Vector3 P(float[] p)=>new Vector3(-p[0],p[2],-p[1]);

        public static void Place(VillageV2Builder.SceneSpec spec,CitadelTraversal traversal)
        {
            Props=DeadTrees=-1;converted.Clear();rng=new System.Random(spec.seed+19);walk=traversal;
            landscape=GameObject.Find("Relief, eau et ouvrages").transform;
            if(!AssetDatabase.IsValidFolder(Pack.TrimEnd('/'))){Debug.LogWarning("Pack tiers absent, décor non posé : "+Pack);return;}
            var root=new GameObject("Décor tiers (Asset Store)").transform;
            Physics.SyncTransforms();
            // Au bourg et au souk : réserves, chariots et lampes le long des rues.
            var village=Group(root,"Réserves et chariots du bourg");int props=0;
            props+=Scatter(village,new[]{"prefab_props/barrel_group","prefab_props/box","prefab_props/barrel"},new Vector3(110,7,45),22,14,2.5f);
            props+=Scatter(village,new[]{"prefab_props/wagon"},new Vector3(118,7,62),20,3,3.5f);
            props+=Scatter(village,new[]{"prefab_props/street_oil_light"},new Vector3(108,8,40),24,6,2.0f);
            // Campement à l'orée de la palmeraie, fontaine et puits près de l'eau.
            var camp=Group(root,"Campement de la palmeraie");
            props+=Scatter(camp,new[]{"prefab_props/tent_a","prefab_props/tent_b","prefab_props/tent_c"},new Vector3(236,4,20),30,4,4.5f);
            props+=Scatter(camp,new[]{"prefab_props/fire_cage"},new Vector3(236,4,20),30,3,2.0f);
            props+=Scatter(camp,new[]{"prefab_props/well","prefab_props/fountain_a"},new Vector3(185,4,85),22,2,3.0f);
            Props=Require(props,"accessoire");
            var trees=Group(root,"Arbres morts de la plaine");
            var names=Enumerable.Range(0,10).Select(i=>"prefab_trees/dead_tree_"+(char)('a'+i)).ToArray();
            DeadTrees=Require(Scatter(trees,names,new Vector3(0,0,0),260,40,5f,120),"arbre mort");
            Debug.Log("DESERT_DECOR_TIERS "+spec.id+" accessoires="+Props+" arbres_morts="+DeadTrees);
        }

        static int Require(int count,string what)
        {
            if(count==0)throw new InvalidOperationException("Aucun "+what+" posé alors que le pack est présent");
            return count;
        }
        static Transform Group(Transform root,string name){var t=new GameObject(name).transform;t.SetParent(root);return t;}

        // Distance horizontale au ruban de rue le plus proche, bord compris.
        static float RouteGap(Vector3 p)
        {
            float best=float.MaxValue;
            foreach(var route in walk.routes)
                for(int i=1;i<route.points.Length;i++)
                {
                    Vector2 a=new(route.points[i-1].x,route.points[i-1].z),b=new(route.points[i].x,route.points[i].z),q=new(p.x,p.z);
                    Vector2 ab=b-a;float t=ab.sqrMagnitude<1e-6f?0:Mathf.Clamp01(Vector2.Dot(q-a,ab)/ab.sqrMagnitude);
                    best=Mathf.Min(best,Vector2.Distance(q,a+ab*t)-route.width/2);
                }
            return best;
        }
        static bool InPlot(Vector3 p,float margin)=>walk.plots.Any(z=>Mathf.Abs(p.x-z.position.x)<z.size.x/2+margin&&Mathf.Abs(p.z-z.position.z)<z.size.y/2+margin);

        static int Scatter(Transform parent,string[] prefabs,Vector3 center,float radius,int count,float clearance,float minRadius=0)
        {
            int placed=0;
            for(int attempt=0;attempt<count*60&&placed<count;attempt++)
            {
                float a=R(0,Mathf.PI*2),r=Mathf.Lerp(minRadius,radius,Mathf.Sqrt((float)rng.NextDouble()));
                var at=new Vector3(center.x+Mathf.Cos(a)*r,0,center.z+Mathf.Sin(a)*r);
                if(RouteGap(at)<clearance||InPlot(at,clearance)||Vector3.Distance(new Vector3(at.x,0,at.z),new Vector3(walk.spawn.x,0,walk.spawn.z))<8)continue;
                var path=Pack+prefabs[rng.Next(prefabs.Length)]+".prefab";
                var prefab=AssetDatabase.LoadAssetAtPath<GameObject>(path);
                if(!prefab)throw new InvalidOperationException("Prefab tiers absent : "+path);
                if(Put(prefab,parent,at,R(0,360)))placed++;
            }
            return placed;
        }

        static bool Put(GameObject prefab,Transform parent,Vector3 at,float yaw)
        {
            // Sol : terrain ou dallage, pente douce, sous toute l'emprise.
            if(!Physics.Raycast(new Vector3(at.x,600,at.z),Vector3.down,out var hit,1200)||!hit.collider.transform.IsChildOf(landscape)||hit.normal.y<.9f)return false;
            if(!hit.collider.name.StartsWith("Terrain_")&&!hit.collider.name.StartsWith("Place_du_souk"))return false;
            var go=(GameObject)PrefabUtility.InstantiatePrefab(prefab,parent);
            // Les modèles Polylised sont exportés axe Z vers le haut (constat de la citadelle).
            go.transform.rotation=Quaternion.Euler(0,yaw,0)*Quaternion.Euler(-90,0,0)*prefab.transform.localRotation;
            go.transform.position=hit.point;Convert(go);
            var renderers=go.GetComponentsInChildren<Renderer>().Where(r=>r.enabled).ToArray();
            if(renderers.Length==0){UnityEngine.Object.DestroyImmediate(go);return false;}
            var b=renderers[0].bounds;foreach(var r in renderers.Skip(1))b.Encapsulate(r.bounds);
            go.transform.position+=Vector3.up*(hit.point.y-b.min.y-.03f);
            b.center+=Vector3.up*(hit.point.y-b.min.y-.03f);
            // Pas de chevauchement avec les maisons, palmiers, échoppes ou un autre accessoire.
            Physics.SyncTransforms();
            var others=Physics.OverlapBox(b.center,b.extents*.9f).Where(c=>!c.transform.IsChildOf(landscape)&&!c.transform.IsChildOf(go.transform)).ToArray();
            if(others.Length>0||RouteGap(b.center)<Mathf.Max(b.extents.x,b.extents.z)){UnityEngine.Object.DestroyImmediate(go);return false;}
            var box=go.AddComponent<BoxCollider>();box.center=go.transform.InverseTransformPoint(b.center);
            box.size=Vector3.Scale(go.transform.InverseTransformVector(b.size),new Vector3(1,1,1));box.size=new Vector3(Mathf.Abs(box.size.x),Mathf.Abs(box.size.y),Mathf.Abs(box.size.z));
            go.isStatic=true;return true;
        }

        static void Convert(GameObject go)
        {
            foreach(var r in go.GetComponentsInChildren<Renderer>(true))
            {
                var materials=r.sharedMaterials;
                if(materials.Any(m=>m&&m.name.EndsWith("colider"))){r.enabled=false;continue;}
                r.sharedMaterials=materials.Select(Desert).ToArray();
            }
        }
        static Material Desert(Material source)
        {
            if(!source)throw new InvalidOperationException("Matériau tiers vide");
            if(converted.TryGetValue(source.name,out var done))return done;
            string n=source.name,scene=null;
            if(n.StartsWith("Wood")||n.StartsWith("Rope"))scene="bois_palmier";
            else if(n.StartsWith("Metal"))scene="fer_noir";
            else if(n=="Wall_0")scene="pierre_taille";
            else if(n=="Wall_1")scene="pise_clair";
            else if(n.StartsWith("Water"))scene="eau_oasis";
            else if(n=="tent_black")scene="tissu_poil";
            else if(n=="Light")scene="lumiere";
            else if(n.StartsWith("Cloth"))scene=new[]{"tissu_ecru","tissu_garance","tissu_indigo","tissu_safran"}[n.Sum(c=>(int)c)%4];
            if(scene==null)throw new InvalidOperationException("Matériau tiers sans correspondance : "+n);
            var m=AssetDatabase.LoadAssetAtPath<Material>(DesertBuilder.Root+"/Materials/"+scene+".mat");
            if(!m)throw new InvalidOperationException("Matériau du désert absent : "+scene);
            return converted[n]=m;
        }
    }
}
