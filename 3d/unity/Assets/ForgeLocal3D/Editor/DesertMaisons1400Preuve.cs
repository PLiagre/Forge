using System;using System.Linq;using Forge.Pont;using UnityEditor;using UnityEngine;using Object=UnityEngine.Object;
namespace ForgeLocal3D
{
    public static class DesertMaisons1400Preuve
    {
        static int echecs;
        public static void Verifier(){int code=1;try{code=Jouer()?0:1;}catch(Exception e){Debug.LogException(e);code=1;}finally{Debug.Log("MAISONS1400 code "+code);EditorApplication.Exit(code);}}
        static void Cas(bool ok,string nom){if(ok)Debug.Log("MAISONS1400 ok "+nom);else{echecs++;Debug.LogError("MAISONS1400 ECHEC "+nom);}}
        static bool Jouer()
        {
            echecs=0;const int N=65;var td=new TerrainData();td.heightmapResolution=N;td.size=new Vector3(1024,40,1024);var h=new float[N,N];for(int z=0;z<N;z++)for(int x=0;x<N;x++)h[z,x]=.15f+.7f*x/(N-1f);td.SetHeights(0,0,h);
            var solGo=Terrain.CreateTerrainGameObject(td);solGo.transform.position=new Vector3(-512,12,-512);var terrain=solGo.GetComponent<Terrain>();var parent=new GameObject("parent");var temoin=new GameObject("Bâtiments du plan");temoin.transform.SetParent(parent.transform,false);
            var cube=GameObject.CreatePrimitive(PrimitiveType.Cube);cube.transform.SetParent(temoin.transform,false);int cubeId=cube.GetInstanceID();var kit=KitDesBatiments.Charger();var dessin=new DesertMaisons1400(parent.transform,terrain,kit);
            var pleine=Base((20,16,0,5,8,1),(-24,18,90,5,8,1),(8,-28,37,5,8,1),(55,8,0,25,32,6));var pose=MaisonsDeLaBase.Poser(pleine);
            Cas(pose.Presente&&pose.Cases.Count>6,"pose "+(pose.Presente?pose.Cases.Count+" cases":pose.Absence));if(!pose.Presente)return false;
            string ligne=dessin.Dessiner(pleine);string une=Decrire(dessin.Racine);
            Cas(dessin.Posees==pose.Cases.Count&&dessin.Foyers==pose.Cases.Count&&dessin.Refus.Count==0&&dessin.Absence==null,"compte "+ligne.Replace("\n"," | "));
            Cas(pose.Cases.Any(c=>c.LacetDegres<.01)&&pose.Cases.Any(c=>Math.Abs(c.LacetDegres-90)<.01)&&pose.Cases.Any(c=>c.LacetDegres%90>1&&c.LacetDegres%90<89),"lacets 0, 90, oblique");
            var ilot=pose.Cases.Where(c=>c.Maison==3).ToArray();Cas(ilot.Length>=4&&ilot.Select(c=>c.Indice).Distinct().Count()>=4,"îlot "+ilot.Length);
            float sA=-1,sB=-1;bool poseOk=dessin.Racine.childCount==pose.Cases.Count;
            for(int i=0;i<pose.Cases.Count&&poseOk;i++)poseOk&=Piece(dessin.Racine.GetChild(i).gameObject,pose.Cases[i],terrain,kit,ref sA,ref sB);
            Cas(poseOk&&Math.Abs(sA-sB)>.05f&&Math.Abs(sA-1f)>.05f,"échelles "+sA.ToString("F3")+" / "+sB.ToString("F3"));
            dessin.Dessiner(pleine);Cas(Decrire(dessin.Racine)==une&&dessin.Posees==pose.Cases.Count,"second dessin, sans doublon");
            Cas(temoin.transform.childCount==1&&cube!=null&&cube.GetInstanceID()==cubeId,"racine témoin intacte");Cas(kit.Maison(0).Prefab.GetComponentInChildren<MeshFilter>(true).sharedMesh!=null,"maillage partagé vivant");
            var go=dessin.Racine.GetChild(0).gameObject;var cas0=pose.Cases[0];var garde=go.transform.localScale;
            go.transform.localScale=garde*3f;bool trop=DesertMaisons1400.Depasse(go,cas0);go.transform.localScale=garde;Cas(trop&&!DesertMaisons1400.Depasse(go,cas0),"garde de débord");
            void Apres(BaseDuPlan b,string quoi,bool absente,string extrait){string l=dessin.Dessiner(b);
                bool zero=!absente&&dessin.Foyers==0&&dessin.Posees==0&&dessin.Absence==null&&l.Contains("0 foyer");
                bool manque=absente&&dessin.Foyers==-1&&dessin.Posees==0&&dessin.Absence!=null&&l.Contains(extrait)&&!l.Contains("0 foyer");
                Cas((absente?manque:zero)&&dessin.Racine.childCount==0&&temoin.transform.childCount==1,quoi+" « "+l.Replace("\n"," | ")+" »");}
            Apres(null,"base absente efface",true,"base non servie");dessin.Dessiner(pleine);
            Apres(new BaseDuPlan(new[]{new PointLocal(0,0),new PointLocal(1,0),new PointLocal(0,1)},new RueDeBase[0],new MaisonDeBase[0]),"base vide efface",false,"0");
            Apres(new BaseDuPlan(new[]{new PointLocal(0,0),new PointLocal(1,0),new PointLocal(0,1)},new RueDeBase[0],new[]{new MaisonDeBase(new[]{new PointLocal(0,2),new PointLocal(5,2),new PointLocal(5,10)},1)}),"pose impossible",true,"emprise");
            Refus(dessin,kit,(20,16,0,5,8,1),(726,0,0,5,8,1),"hors du terrain","726 m");
            Refus(dessin,kit,(20,16,0,5,8,1),(508,0,20,5,8,1),"hors du terrain","un coin");
            var copie=Object.Instantiate(kit);copie.maisonsPise=(GameObject[])kit.maisonsPise.Clone();copie.maisonsPise[1]=null;
            Refus(new DesertMaisons1400(parent.transform,terrain,copie),copie,(20,16,0,5,8,1),(-24,18,90,5,8,1),"référence absente","référence absente");
            var vide=Object.Instantiate(kit);vide.maisonsPise=(GameObject[])kit.maisonsPise.Clone();vide.maisonsPise[1]=new GameObject("sans maillage");
            Refus(new DesertMaisons1400(parent.transform,terrain,vide),vide,(20,16,0,5,8,1),(-24,18,90,5,8,1),"mesure absente","mesure absente");
            Cas(temoin.transform.childCount==1,"témoin après les refus");return echecs==0;
        }
        static void Refus(DesertMaisons1400 d,KitDesBatiments kit,(double x,double y,double lac,double lar,double pro,int k) bon,(double x,double y,double lac,double lar,double pro,int k) mauvais,string cause,string nom)
        {
            var b=Base(bon,mauvais);var pose=MaisonsDeLaBase.Poser(b);string l=d.Dessiner(b);
            bool ok=pose.Presente&&d.Foyers==pose.Cases.Count&&d.Posees==pose.Cases.Count(c=>c.Maison==0)&&d.Posees>=1&&d.Refus.Count==pose.Cases.Count(c=>c.Maison==1)
                &&d.Refus.All(r=>r.Contains("Maison 1")&&r.Contains(cause))&&d.Racine.childCount==d.Posees;
            if(ok&&cause=="hors du terrain")ok&=pose.Cases.Where(c=>c.Maison==1).All(c=>DesertMaisons1400.Coins(c).Any(p=>Math.Abs(p.x)>511f||Math.Abs(p.y)>511f))
                &&pose.Cases.Where(c=>c.Maison==0).All(c=>DesertMaisons1400.Coins(c).All(p=>Math.Abs(p.x)<=511f&&Math.Abs(p.y)<=511f));
            Cas(ok,nom+" « "+l.Replace("\n"," | ")+" »");if(d.Posees>0)Cas(Meme(d.Racine.GetChild(0).gameObject,kit.Maison(0).Prefab),nom+" variante");
        }
        static bool Piece(GameObject go,CaseDeMaison c,Terrain terrain,KitDesBatiments kit,ref float sA,ref float sB)
        {
            var prefab=kit.Maison((c.Maison+c.Indice)%6).Prefab;if(!Meme(go,prefab)||!DesertMaisons1400.Boite(prefab,out var boite))return false;
            float att=Mathf.Min((float)c.LargeurM/boite.size.x,(float)c.ProfondeurM/boite.size.z);var s=go.transform.localScale;
            if(Mathf.Abs(s.x-att)>1e-3f||Mathf.Abs(s.x-s.y)>1e-4f||Mathf.Abs(s.y-s.z)>1e-4f)return false;
            if(Quaternion.Angle(go.transform.rotation,Quaternion.Euler(0,(float)c.LacetDegres,0))>.2f||go.transform.up.y<.999f)return false;
            if(c.Maison<3&&Math.Abs(c.LargeurM-5)<.01)sA=s.x;if(c.Maison==3)sB=s.x;
            float minX=1e30f,maxX=-1e30f,minZ=minX,maxZ=maxX,bas=minX,sol=minX,haut=maxX;
            foreach(var f in go.GetComponentsInChildren<MeshFilter>(true)){if(!f.sharedMesh)continue;var box=f.sharedMesh.bounds;for(int k=0;k<8;k++){
                var m=f.transform.TransformPoint(new Vector3((k&1)==0?box.min.x:box.max.x,(k&2)==0?box.min.y:box.max.y,(k&4)==0?box.min.z:box.max.z));
                minX=Mathf.Min(minX,m.x);maxX=Mathf.Max(maxX,m.x);minZ=Mathf.Min(minZ,m.z);maxZ=Mathf.Max(maxZ,m.z);bas=Mathf.Min(bas,m.y);
                double t=c.LacetDegres*Math.PI/180,px=-m.x-c.CentreX,py=-m.z-c.CentreY,u=px*-Math.Cos(t)+py*Math.Sin(t),v=px*-Math.Sin(t)+py*-Math.Cos(t);
                double ox=Math.Max(0,Math.Abs(u)-c.LargeurM/2),oz=Math.Max(0,Math.Abs(v)-c.ProfondeurM/2);if(ox*ox+oz*oz>.05*.05)return false;}}
            foreach(var p in DesertMaisons1400.Coins(c)){float y=terrain.SampleHeight(new Vector3(-p.x,0,-p.y))+terrain.transform.position.y;sol=Mathf.Min(sol,y);haut=Mathf.Max(haut,y);}
            float centre=terrain.SampleHeight(new Vector3(-(float)c.CentreX,0,-(float)c.CentreY))+terrain.transform.position.y;
            return Mathf.Abs((minX+maxX)/2+(float)c.CentreX)<.01f&&Mathf.Abs((minZ+maxZ)/2+(float)c.CentreY)<.01f&&Mathf.Abs(bas-sol)<.01f&&haut-sol>.02f&&Mathf.Abs(centre-sol)>.01f;
        }
        static bool Meme(GameObject go,GameObject prefab)=>go.GetComponentsInChildren<MeshFilter>(true).Select(f=>f.sharedMesh).SequenceEqual(prefab.GetComponentsInChildren<MeshFilter>(true).Select(f=>f.sharedMesh));
        static string Decrire(Transform r){var s="";for(int i=0;i<r.childCount;i++){var t=r.GetChild(i);s+=t.name+" "+t.position.ToString("F3")+" "+t.eulerAngles.ToString("F2")+" "+t.localScale.ToString("F4")+"\n";}return s;}
        static BaseDuPlan Base(params (double x,double y,double lac,double lar,double pro,int k)[] hs)
        {
            var rues=new RueDeBase[hs.Length];var mais=new MaisonDeBase[hs.Length];
            for(int i=0;i<hs.Length;i++){double t=hs[i].lac*Math.PI/180,wx=-Math.Cos(t),wy=Math.Sin(t),dx=-Math.Sin(t),dy=-Math.Cos(t),hw=hs[i].lar/2,hd=hs[i].pro/2;
                PointLocal C(double u,double v)=>new PointLocal(hs[i].x+u*wx+v*dx,hs[i].y+u*wy+v*dy);
                mais[i]=new MaisonDeBase(new[]{C(-hw,-hd),C(hw,-hd),C(hw,hd),C(-hw,hd)},hs[i].k);rues[i]=new RueDeBase(new[]{C(-18,hd+3),C(18,hd+3)},6,"principale");}
            return new BaseDuPlan(new[]{new PointLocal(0,0),new PointLocal(1,0),new PointLocal(0,1)},rues,mais);
        }
    }
}
