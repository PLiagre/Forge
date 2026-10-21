using System;using System.Collections.Generic;using System.Linq;using Forge.Pont;using UnityEditor;using UnityEngine;using UnityEngine.Rendering;
namespace ForgeLocal3D
{
    // Lot 738 : les rubans de la base suivent le sol sans toucher au terrain (SC1), et se redessinent quand le sol change (SC2).
    public static class DesertRues1400Preuve
    {
        static int echecs;
        public static void Verifier(){int code=1;try{code=Jouer()?0:1;}catch(Exception e){Debug.LogException(e);code=1;}finally{Debug.Log("RUES1400 code "+code);EditorApplication.Exit(code);}}
        static void Cas(bool ok,string nom){if(ok)Debug.Log("RUES1400 ok "+nom);else{echecs++;Debug.LogError("RUES1400 ECHEC "+nom);}}
        // Le sol, en mètres : pente de 0,03 en z, et une crête en x = 40 du monde dont la pente passe de +0,25 à −0,25.
        static float Sol(int x,int z)=>30f+.03f*(z-512f)+5f-.25f*Mathf.Min(Mathf.Abs(x-512f-40f),20f);
        static bool Jouer()
        {
            echecs=0;const int N=1025;var td=new TerrainData();td.heightmapResolution=N;td.size=new Vector3(1024,100,1024);td.terrainLayers=new[]{new TerrainLayer()};var h=new float[N,N];for(int z=0;z<N;z++)for(int x=0;x<N;x++)h[z,x]=Sol(x,z)/100f;td.SetHeights(0,0,h);
            var terrain=Terrain.CreateTerrainGameObject(td).GetComponent<Terrain>();terrain.transform.position=new Vector3(-512,12,-512);var parent=new GameObject("outil");var temoin=new GameObject("Maisons de 1400");temoin.transform.SetParent(parent.transform,false);var cube=GameObject.CreatePrimitive(PrimitiveType.Cube);cube.transform.SetParent(temoin.transform,false);
            var couche=new TerrainLayer{diffuseTexture=new Texture2D(4,4),tileSize=new Vector2(4,4),diffuseRemapMax=new Vector4(.78f,.64f,.5f,1)};var dessin=new DesertRues1400(parent.transform,terrain,couche);double lp=Math.Sqrt(7400),ux=-70/lp,uy=50/lp,bx=-45-uy*3,by=-5+ux*3;
            var pleine=new BaseDuPlan(new[]{new PointLocal(0,0)},new[]{Rue(6,(-10,-30),(-80,20)),Rue(3,(bx,by),(bx-uy*25,by+ux*25)),Rue(6,(400,100),(700,100)),Rue(3,(600,600),(700,650)),Rue(6,(0,0)),Rue(0,(0,0),(10,0))},new MaisonDeBase[0]);
            string avant=DesertRoads.Empreintes(td).Tout,ligne=dessin.Dessiner(pleine),une=dessin.Empreinte;var rel=Releve(dessin.Racine);
            Cas(dessin.Servies==6&&dessin.Dessinees==3&&dessin.Coupees==1&&dessin.HorsDuTerrain==1&&dessin.Refus.Count==2&&dessin.Refus[0].Contains("rang 4")&&dessin.Refus[1].Contains("rang 5")
                &&ligne.StartsWith("Rues de 1400 : 3 dessinée(s) sur 6, 1 coupée(s) au bord du terrain, 1 hors du terrain\n",StringComparison.Ordinal),"compteurs « "+ligne.Replace("\n"," | ")+" »");
            var e=Ecart(rel,terrain);Cas(rel.Count==3&&Dans(e),"ruban − sol "+e);var troue=rel.Select((r,k)=>(r.s,k==1?new int[0]:r.t,r.uv)).ToList();
            Cas(!Dans(Ecart(troue,terrain))&&!Sorti(Ecart(troue,terrain))&&!Dans(Ecart(rel.Take(0).ToList(),terrain)),"contre-épreuve : un ruban sans triangle, ou aucun ruban, ne se mesure pas");
            Cas(rel.All(r=>Enumerable.Range(0,r.t.Length/3).All(k=>Vector3.Cross(r.s[r.t[3*k+1]]-r.s[r.t[3*k]],r.s[r.t[3*k+2]]-r.s[r.t[3*k]]).y>0)),"triangles vers le ciel");
            Axe(rel,0,-10,-30,ux,uy,6,lp);Axe(rel,1,bx,by,-uy,ux,3,25);Axe(rel,2,400,100,1,0,6,108);
            Cas(rel.All(r=>r.s.All(v=>Mathf.Abs(v.x)<=511.01f&&Mathf.Abs(v.z)<=511.01f))&&Mathf.Abs(rel[2].s.Max(v=>-v.x)-508f)<.01f,"rue coupée à 508 m, chaussée dans 511 m");
            Cas(rel.All(r=>Enumerable.Range(0,r.s.Length).All(k=>Vector2.Distance(r.uv[k],new Vector2(r.s[k].x/4f,r.s[k].z/4f))<1e-4f)),"UV du monde sur tileSize");
            Cas(dessin.Racine.GetComponentsInChildren<Collider>().Length==0&&dessin.Racine.GetComponentsInChildren<MeshRenderer>().All(m=>m.shadowCastingMode==ShadowCastingMode.Off&&m.sharedMaterial.mainTexture==couche.diffuseTexture),"sans ombre ni collider, texture de la couche");
            dessin.Dessiner(pleine);Cas(dessin.Empreinte==une&&dessin.Racine.childCount==3&&Dans(Ecart(Releve(dessin.Racine),terrain))&&DesertRoads.Empreintes(td).Tout==avant,"second dessin identique, sans doublon, terrain intact");
            // SC2 : une bosse de 0,5 m sous le milieu de la principale (monde 45, 5).
            var b=td.GetHeights(553,513,9,9);for(int z=0;z<9;z++)for(int x=0;x<9;x++)b[z,x]+=.005f*Mathf.Max(0,1-Mathf.Max(Mathf.Abs(x-4),Mathf.Abs(z-4))/4f);td.SetHeights(553,513,b);
            var vieux=Ecart(rel,terrain);dessin.Dessiner(pleine);var neuf=Ecart(Releve(dessin.Racine),terrain);Cas(Sorti(vieux)&&vieux.min<-.3f&&Dans(neuf)&&dessin.Racine.childCount==3,"bosse : anciens sommets "+vieux+", redessinés "+neuf);
            void Apres(BaseDuPlan bp,string quoi,Func<string,bool> ok,Action entre=null){dessin.Dessiner(pleine);bool plein=dessin.Racine.childCount==3;entre?.Invoke();string l=dessin.Dessiner(bp);
                Cas(plein&&ok(l)&&dessin.Racine.childCount==0&&temoin.transform.childCount==1&&cube,quoi+" « "+l.Replace("\n"," | ")+" »");}
            Apres(null,"base nulle",l=>dessin.Absence!=null&&l.Contains("base non servie")&&!l.Contains("0 dessinée"));
            Apres(new BaseDuPlan(new[]{new PointLocal(0,0)},new RueDeBase[0],new MaisonDeBase[0]),"base sans rue",l=>dessin.Absence==null&&l=="Rues de 1400 : 0 dessinée(s) sur 0, 0 coupée(s) au bord du terrain, 0 hors du terrain");
            Apres(pleine,"couche sans texture",l=>dessin.Absence!=null&&l.Contains("sans texture")&&!l.Contains("0 dessinée"),()=>couche.diffuseTexture=null);return echecs==0;
        }
        static RueDeBase Rue(double w,params (double x,double y)[] p)=>new RueDeBase(p.Select(q=>new PointLocal(q.x,q.y)).ToArray(),w,w>=6?"principale":"ruelle");
        internal static List<(Vector3[] s,int[] t,Vector2[] uv)> Releve(Transform r)=>r.Cast<Transform>().Select(c=>{var m=c.GetComponent<MeshFilter>().sharedMesh;return (m.vertices.Select(c.TransformPoint).ToArray(),m.triangles,m.uv);}).ToList();
        // Écart ruban − sol au centre et aux milieux d'arête de chaque triangle. Aucun ruban, ou un ruban sans triangle, ne se mesure pas :
        // NaN, qui n'est ni dans la fenêtre (Dans) ni hors d'elle (Sorti), si bien qu'un échantillon vide échoue des deux côtés.
        internal static (float min,float max) Ecart(List<(Vector3[] s,int[] t,Vector2[] uv)> rel,Terrain t)
        {
            float lo=1e9f,hi=-1e9f;if(rel.Count==0||rel.Any(r=>r.t.Length<3))return (float.NaN,float.NaN);
            foreach(var (s,tr,_) in rel)for(int k=0;k<tr.Length;k+=3){Vector3 a=s[tr[k]],b=s[tr[k+1]],c=s[tr[k+2]];
                foreach(var q in new[]{(a+b+c)/3,(a+b)/2,(b+c)/2,(c+a)/2}){float e=q.y-t.SampleHeight(q)-t.transform.position.y;lo=Mathf.Min(lo,e);hi=Mathf.Max(hi,e);}}
            return (lo,hi);
        }
        internal static bool Dans((float min,float max) e)=>e.min>=.01f&&e.max<=.15f;internal static bool Sorti((float min,float max) e)=>e.min<.01f||e.max>.15f;
        // Demi-largeur à 0,01 m près, et longueur dessinée le long de l'axe, à un pas près.
        static void Axe(List<(Vector3[] s,int[] t,Vector2[] uv)> rel,int i,double ax,double ay,double ux,double uy,double w,double longueur)
        {
            double lo=1e9,hi=-1e9,large=0;foreach(var v in rel[i].s){double px=-v.x-ax,py=-v.z-ay,a=px*ux+py*uy;lo=Math.Min(lo,a);hi=Math.Max(hi,a);large=Math.Max(large,Math.Abs(px*uy-py*ux));}
            Cas(Math.Abs(large-w/2)<.01&&Math.Abs(hi-lo-longueur)<=DesertRues1400.Pas,"rue "+i+" : demi-largeur "+large.ToString("F3")+", longueur "+(hi-lo).ToString("F2")+" sur "+longueur.ToString("F2"));
        }
    }
}
